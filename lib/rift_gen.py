from lib import utils
import os

class RIFTGenerator:


    def __init__(self, logger, rift_config, compile_info):
        self.logger = logger
        self.rift_config = rift_config
        self.compile_info = compile_info

    def gen_pat(self, coff_files, dest):

        pat_files = []
        for coff_file in coff_files:
            pat_file = os.path.basename(coff_file)
            pat_file = os.path.join(dest, pat_file.replace(".o", ".pat"))
            cmd = [self.rift_config.pcf, coff_file, pat_file]
            self.logger.debug(f"Executing {' '.join(cmd)}")
            utils.exec_cmd(cmd, True, True)
 
            pat_files.append(pat_file)
        return pat_files
    
    def gen_flirt(self, pat_folder, flirt_output, ignore_collisions=True):
        cur_path = os.getcwd()
        cmd = [self.rift_config.sigmake]
        if ignore_collisions:
            cmd.append("-r")
        cmd.extend(["*", flirt_output])
        os.chdir(pat_folder)
        self.logger.debug(f"Executing {' '.join(cmd)}")
        utils.exec_cmd(cmd, True, True)
        os.chdir(cur_path)
        return True
    
    def get_rustc_flirt_name(self):
        return f"rustc-{self.compile_info['rust_version']}-{self.compile_info['target']}-{self.compile_info['compile_type']}.sig"
    
    def get_flirt_name(self, crate):
        return f"{crate}-{self.compile_info['rust_version']}--{self.compile_info['target']}-{self.compile_info['compile_type']}.sig"
    
    def set_dph_env(self, use_decompiler):
        os.environ["DIAPHORA_AUTO"] = "1"
        if use_decompiler:
            os.environ["DIAPHORA_USE_DECOMPILER"] = "1"
    
    def dph_env_cleanup(self):
        """Cleans up the Diaphora environment variables by setting them to '0' or an empty string."""
        os.environ["DIAPHORA_AUTO"] = "0"
        os.environ["DIAPHORA_USE_DECOMPILER"] = "0"
        os.environ["DIAPHORA_EXPORT_FILE"] = ""

    def set_dph_export_file(self, export_file):
        os.environ["DIAPHORA_EXPORT_FILE"] = export_file

    def gen_sqlite(self, coff_files, sql_folder, idb_folder):
        for coff_file in coff_files:

            sql_fname = utils.replace_extension(os.path.basename(coff_file), ".sqlite")
            idb_fname = utils.replace_extension(os.path.basename(coff_file), ".idb")
            sql_path = os.path.join(sql_folder, sql_fname)
            idb_path = os.path.join(idb_folder, idb_fname)

            self.logger.info(f"Generating {sql_path} ..")
            cmd = [self.rift_config.idat, "-A", "-B", f"-S{self.rift_config.diaphora}", f"-o{idb_path}", coff_file]
            self.set_dph_export_file(sql_path)
            utils.exec_cmd(cmd, True, True)

    def dph_diff(self, target_sqlite, src_sqlite_files, sql_diff_folder):
        target_base = os.path.splitext(os.path.basename(target_sqlite))[0]
        for src_sqlite in src_sqlite_files:
            src_base = os.path.splitext(os.path.basename(src_sqlite))[0]
            output_path = os.path.join(sql_diff_folder, f"{target_base}_{src_base}.sqlite")
            self.logger.info(f"Generating {output_path}, target = {target_sqlite}, source = {src_sqlite}")
            utils.exec_cmd(["py", self.rift_config.diaphora, "-o", output_path, target_sqlite, src_sqlite], capture_output=False, check=False)
        return True