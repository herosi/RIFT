from lib import utils
from lib.config_handler import ConfigHandler
from lib.err_parser import ErrorParser
from copy import copy
import re
import os
import subprocess

class RIFTCompiler:

    def __init__(self, logger, compile_info, cargo_proj_path):
        self.cargo_proj_path = cargo_proj_path
        self.logger = logger
        self.compile_debug = False
        self.rust_version = None
        self.commithash = compile_info["commithash"]
        self.crates = compile_info["crates"]
        self.arch = compile_info["arch"]
        self.target_triple = compile_info["target_triple"]
        self.rustc_hashes_path = "data/rustc_hashes.json"
        self.cfg_handler = ConfigHandler(self.cargo_proj_path, self.logger)
        #TODO: Keep this enabled for now
        self.autofix_errors = True

    def determine_rust_version(self):
        json_data = utils.read_json(self.rustc_hashes_path)
        hash_data = json_data["exact_hash_to_version"]
        rust_version_determined = False
        for j in hash_data:
            commithash = j["commit_hash"]
            if self.commithash == commithash:
                self.rust_version = j["rust_version"]
                rust_version_determined = True
                self.logger.info(f"Commit Hash = {self.commithash}, RustVersion = {self.rust_version}")
                break
        return rust_version_determined
    
    def init_target_compiler(self):
        
        target_compiler = self.get_target_compiler()
        if target_compiler not in self.get_installed_toolchains():
            self.logger.info(f"Installing target_compiler = {target_compiler}")
            if not self.install_target_compiler(target_compiler):
                self.logger.error(f"Could not install target_compiler = {target_compiler}")
                return False
        
        target = self.get_target()
        if target not in self.get_added_targets():
            self.logger.info(f"Adding target = {target}")
            if not self.add_target(target):
                self.logger.error(f"Could not add target = {target}")
                return False
        return True

    def set_crates(self):

        cur_path = os.getcwd()
        os.chdir(self.cargo_proj_path)
        if not self.cfg_handler.init_proj_config():
            self.logger.error(f"Failed initialzing project configs!")
            return False
        crates_info = self.get_crates_info()
        if not self.cfg_handler.insert_crates(crates_info):
            self.logger.error(f"ConfigHandler could not add crates!")
            return False

        os.chdir(cur_path)
        return True
    
    def set_toolchain_config(self):
        toolchain_info = {"channel": f"\"{self.rust_version}\"", "targets": f"[ \"{self.get_target()}\" ]"}
        if not self.cfg_handler.create_toolchain_config(toolchain_info):
            self.logger.error(f"ConfigHandler could not initialize toolchain file!")
            return False
        return True

    def set_cargo_config(self):
        # TODO: A little bit confused by this. Apparently there is a difference whether arrays can be passed or not for different rust versions
        # For rust 1.63.0, setting this as an array will result in an error. We default to non array for now
        # cargo_config_data = {"target": f"[ \"{target}\" ]"}
        cargo_config_info = {"target": f"\"{self.get_target()}\""}
        if not self.cfg_handler.create_cargo_config(cargo_config_info):
            self.logger.error(f"ConfigHandler failed initializing cargo config file!")
            return False
        return True
    
    def build_crates(self):

        cur_dir = os.getcwd()
        os.chdir(self.cargo_proj_path)
        target_crates = list(self.get_crates_info().keys())
        result = {"compiled_crates": [], "failed_crates": []}
        # Init counter and command templates
        i = 0
        check_templ = ["cargo", "check"]
        compile_templ = ["cargo", "build"]

        if self.compile_debug:
            check_templ.append("--debug")
            compile_templ.append("--debug")
        else:
            check_templ.append("--release")
            compile_templ.append("--release")
        check_templ.append("--package")
        compile_templ.append("--package")
        err_parser = ErrorParser(self.logger)
        while i < len(target_crates):

            crate = target_crates[i]
            check_cmd = copy(check_templ)
            check_cmd.append(crate)
            compile_cmd = copy(compile_templ)
            compile_cmd.append(crate)
            resultcode = 1
            stdout = None
            stderr = None

            self.logger.debug(f"Executing {' '.join(check_cmd)} for crate {crate}")
            try:
                resultcode,stdout,stderr = utils.exec_cmd(check_cmd, capture_output=True, check=True)
            except subprocess.CalledProcessError:
                i += 1
                self.logger.error(f"CalledProcessError occured for {check_cmd}, skipping crate = {crate}")
                result["failed_crates"].append(crate)
                continue
            if resultcode != 0 and self.autofix_errors:
                fix_success = self.__fix_error(stderr, err_parser)
                # We succeeded in fixing the issue? Try again!
                if fix_success:
                    self.logger.info(f"Error fixed! Trying to check if {crate} is compilable again ..")
                    continue
                else:
                    self.logger.info(f"Autofix failed for crate = {crate}, try fixing issue manually. Skipping the crate")
                    result["failed_crates"].append(crate)
                    i += 1
                    continue
            else:
                # Compile now
                self.logger.debug(f"cmd = {' '.join(check_cmd)} success! building the crate now ..")
                try:
                    resultcode,stdout,stderr = utils.exec_cmd(compile_cmd, capture_output=False, check=True)
                except subprocess.CalledProcessError:
                    i += 1
                    self.logger.error(f"CalledProcessError ocurred when trying to compile {crate}, skipping it ..")
                    result["failed_crates"].append(crate)
                    continue
                self.logger.info(f"cmd = {' '.join(compile_cmd)} , resultcode = {resultcode}")
                i += 1
                result["compiled_crates"].append(crate)

        os.chdir(cur_dir)
        return result

    def get_proj_config(self):
        proj_config = {"arch": self.arch, 
                       "target": self.get_target(), 
                       "rust_version": self.rust_version, 
                       "target_compiler": self.get_target_compiler(), 
                       "proj_path": self.cargo_proj_path, 
                       "compile_type": "release"}
        return proj_config


    def __fix_error(self, stderr, err_parser):
        """If autofix is enabled, try to fix errors in the Cargo.toml file."""
        err = err_parser.parse_error_msg(stderr)
        self.logger.debug(err)
        error_code = err["error"]
        entity = err["entity"]
        entity_meta = err["entity_meta"]
        is_success = True

        if error_code == "UNKNOWN_ERROR":

            self.logger.info(f"Unknown error occurred!")
            is_success = False

        elif error_code in ["INVALID_VERSION", "INVALID_VERSION_FOR_REQ_P"]:

            self.logger.info(f"Invalid version detected for {entity}")
            version = self.cfg_handler.get_crate_version(entity)
            version = version.replace("\"=", "\"")
            self.cfg_handler.update_crate(entity, version)
            self.logger.info(f"Updated crate {entity}, less specific now")

        elif error_code == "VERSION_TOO_HIGH":

            self.logger.info(f"Version too high, downgrading version for {entity_meta}")
            new_version = utils.downgrade_version(entity_meta)
            try:
                self.downgrade_crate(entity, entity_meta, new_version)
            except subprocess.CalledProcessError:
                self.logger.warning(f"Failed downgrading crate = {entity}, autofix failed!")
                is_success = False

        elif error_code == "INVALID_CRATE" or error_code == "SYNTAX_ERROR_CRATE":

            line_num = int(entity, 10)
            self.logger.info(f"Manually removing line_num = {line_num} from {self.cfg_handler.cargo_proj_path}")
            utils.remove_line(self.cfg_handler.cargo_proj_path, line_num)

        elif error_code == "NO_MATCHING_PACKAGE":

            self.logger.info(f"No matching package for {entity}")
            self.cfg_handler.remove_crate(entity)

        elif error_code == "WRONG_EDITION" or error_code == "WRONG_EDITION2":
            self.logger.info(f"Wrong edition = {entity} set, downgrading edition ..")
            self.cfg_handler.downgrade_edition()

        return is_success

    def downgrade_crate(self, crate, old_ver, new_ver):
        """Downgrade a specific crate via cargo"""
        # cargo update -p native-tls@0.2.14 --precise ver
        cmd = ["cargo", "update", "-p", f"{crate}@{old_ver}", "--precise", new_ver]
        self.logger.info(f"Executing downgrade: {' '.join(cmd)}")
        resultcode,stdout,stderr = utils.exec_cmd(cmd, capture_output=False)
        return resultcode == 0

    def get_target(self):
        return f"{self.arch}-{self.target_triple}"

    def add_target(self, target):
        cmd = ["rustup", "target", "add", target]
        code, stdout, stderr = utils.exec_cmd(cmd, False)
        if code != 0:
            return 0
        return 1
    
    def get_added_targets(self):
        # cmd = "rustup target list"
        cmd = ["rustup", "target", "list"]
        output = []
        code, stdout, stderr = utils.exec_cmd(cmd, True)
        if code != 0:
            self.logger.error(f"Failed querying added targets!")
            return output
        output = stdout.split("\n")
        for target in output:
            if "(installed)" in target:
                target = target.split(" ")[0]
                output.append(target)
        return output

    def get_installed_toolchains(self):
        """List all installed toolchains."""
        cmd = ["rustup", "toolchain", "list"]
        output = []
        code, stdout, stderr = utils.exec_cmd(cmd, True)
        if code != 0:
            self.logger.error(f"Failed querying installed toolchains!")
            return output
        output = stdout.split("\n")
        return output
    
    def install_target_compiler(self, target_compiler):
        """Try installing a specific target compiler."""
        cmd = ["rustup", "toolchain", "install", target_compiler]
        code, stdout, stderr = utils.exec_cmd(cmd, True)
        if code != 0:
            self.logger.error(stderr)
            return 0
        return 1

    def get_target_compiler(self):
        """Generate the target compiler by concatenating rustc version, arch and target_triple. Returns target compiler as string"""
        return f"{self.rust_version}-{self.arch}-{self.target_triple}"
    
    def get_crates_info(self):
        """"Helper function transforming the crates list to a dictionary ready to insert into toml file."""

        crates_dict = {}
        for crate in self.crates:

            # color-spantrace-0.2.0
            m = re.match(r"(.*)-(\d+\..*)", crate)
            if m:
                # needs hyphen included to match toml format
                crates_dict[m.group(1)] = f"\"={m.group(2)}\""
                continue
        return crates_dict
