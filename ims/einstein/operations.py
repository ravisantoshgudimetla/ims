#!/usr/bin/python
import base64
import io
import subprocess
import time

import ims.common.config as config
from ims.database import *
from ims.einstein.ceph_wrapper import *
from ims.einstein.haas_wrapper import *
from ims.exception import *
from ims.common.log import *


class BMI:
    def __init__(self, credentials):
        self.config = config.get()
        self.logger = create_logger(self.config.logs_url,__name__, self.config.logs_debug, self.config.logs_verbose)
        self.__process_credentials(credentials)
        self.haas = HaaS(base_url=self.config.haas_url, usr=self.username,
                         passwd=self.password)

    def __does_project_exist(self):
        pr = ProjectRepository()
        pid = pr.fetch_id_with_name(self.project)
        # None as a query result implies that the project does not exist.
        if pid is None:
            raise db_exceptions.ProjectNotFoundException(self.project)

        self.pid = pid

    def __get__ceph_image_name(self, name):
        imgr = ImageRepository()
        img_id = imgr.fetch_id_with_name_from_project(name, self.project)
        if img_id is None:
            raise db_exceptions.ImageNotFoundException(name)
        return "img" + str(img_id)

    def __process_credentials(self, credentials):
        base64_str, self.project = credentials
        self.__does_project_exist()
        self.username, self.password = tuple(
            base64.b64decode(base64_str).split(':'))

    def __update_tftp(self, node_name, img_name, target_name):
        mac_addr = "01-" + self.haas.get_node_mac_addr(node_name).replace(":",
                                                                          "-")
        ipxe = self.__generate_ipxe_file(node_name, target_name)
        self.__generate_mac_addr_file(img_name, ipxe, mac_addr)

    def __generate_ipxe_file(self, node_name, target_name):
        template_loc = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        name = node_name + ".ipxe"
        path = self.config.ipxe_loc + name
        with io.open(path, 'w') as ipxe:
            for line in io.open(template_loc + "/ipxe.temp", 'r'):
                line = line.replace(constants.IPXE_TARGET_NAME, target_name)
                ipxe.write(line)
        os.chmod(path, 0755)
        return name

    def __generate_mac_addr_file(self, img_name, ipxe, mac_addr):
        template_loc = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        path = self.config.pxelinux_loc + mac_addr
        with io.open(path, 'w') as mac:
            for line in io.open(template_loc + "/mac.temp", 'r'):
                line = line.replace(constants.MAC_IMG_NAME, img_name)
                line = line.replace(constants.MAC_IPXE_NAME, ipxe)
                mac.write(line)
        os.chmod(path, 0644)


    # Calling shell script which executes a iscsi update as we don't have
    # rbd map in documentation.
    def __call_shellscript(self,*args):
        self.logger.debug("Entering call_shellscript")
        arglist = list(args)
        self.logger.debug("Got parameters = %s",arglist)
        self.logger.debug("Creating process")
        proc = subprocess.Popen(arglist, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        self.logger.debug("Created Process")
        self.logger.debug("Calling Communicate")
        ret = proc.communicate()
        self.logger.debug("Got output = %s after communicate",ret)
        self.logger.debug("Exiting call_shell_script")
        return ret

    # A custom function which is wrapper around only success code that
    # we are creating.
    @staticmethod
    def __return_success(obj):
        return {constants.STATUS_CODE_KEY: 200,
                constants.RETURN_VALUE_KEY: obj}

    # Parses the Exception and returns the dict that should be returned to user
    @staticmethod
    def return_error(ex):

        # Replaces the image name with id in error string
        def swap_id_with_name(err_str):
            parts = err_str.split(" ")
            imgr = ImageRepository()
            name = imgr.fetch_name_with_id(parts[0][3:])
            if name is not None:
                parts[0] = name
            return " ".join(parts)

        if FileSystemException in ex.__class__.__bases__:
            return {constants.STATUS_CODE_KEY: ex.status_code,
                    constants.MESSAGE_KEY: swap_id_with_name(str(ex))}
        return {constants.STATUS_CODE_KEY: ex.status_code,
                constants.MESSAGE_KEY: str(ex)}

    # Provisions from HaaS and Boots the given node with given image
    def provision(self, node_name, img_name, network, channel,nic):
        try:
            self.logger.debug("Entered Provision")
            self.logger.debug(
                "Got parameters = %s %s %s %s", node_name, img_name,
                network, channel, nic)
            self.logger.info(
                "Attaching Node %s to network %s", node_name, network)
            self.haas.attach_node_to_project_network(node_name, network,
                                                     channel, nic)
            self.logger.info("Successfully Attached Node %s to network %s",
                             node_name, network)

            with RBD(self.config.fs[
                         constants.CEPH_CONFIG_SECTION_NAME]) as fs:
                imgr = ImageRepository()
                imgr.insert(node_name, self.pid, is_provision_clone=True)
                clone_img_id = self.__get__ceph_image_name(node_name)

                img_id = self.__get__ceph_image_name(img_name)
                self.logger.info("Cloning image %s as %s", img_id,clone_img_id)
                fs.clone(str(img_id).encode('utf-8'),
                         constants.DEFAULT_SNAPSHOT_NAME.encode('utf-8'),
                         str(clone_img_id).encode("utf-8"))
                self.logger.info("Successfully Finished Cloning image %s as %s",
                    img_id,
                    clone_img_id)
                ceph_config = self.config.fs[
                    constants.CEPH_CONFIG_SECTION_NAME]
                self.logger.debug("Contents of ceph_config = %s",
                                  str(ceph_config))
                # Should be changed to python script
                self.logger.info(
                    "Calling ISCSI shellscript with create command")
                iscsi_output = BMI.__call_shellscript(
                    self.config.iscsi_update,
                    ceph_config[
                        constants.CEPH_KEY_RING_KEY],
                    ceph_config[
                        constants.CEPH_ID_KEY],
                    ceph_config[
                        constants.CEPH_POOL_KEY],
                    str(clone_img_id),
                    constants.ISCSI_CREATE_COMMAND,
                    self.config.iscsi_update_password)
                if constants.ISCSI_UPDATE_SUCCESS in iscsi_output[0]:
                    self.logger.debug("Got Message from ISCSI Script = %s",iscsi_output)
                    self.__update_tftp(node_name, img_name, clone_img_id)
                    return BMI.__return_success(True)

                elif constants.ISCSI_UPDATE_FAILURE in iscsi_output[0]:
                    # Was not able to test this exception in test cases as the haas
                    # call was blocking this exception
                    # But it was raised during preparation of tests
                    # Rare exception
                    self.logger.debug("Raising Node Already In Use Exception")
                    raise iscsi_exceptions.NodeAlreadyInUseException()
        except ISCSIException as e:
            self.logger.exception(
                '')  # Message is being handled by custom formatter
            clone_img_id = self.__get__ceph_image_name(node_name)
            with RBD(self.config.fs[
                         constants.CEPH_CONFIG_SECTION_NAME]) as fs:
                fs.remove(clone_img_id)
            imgr = ImageRepository()
            imgr.delete_with_name_from_project(node_name, self.project)
            time.sleep(30)
            self.haas.detach_node_from_project_network(node_name, network,
                                                       nic)
            return BMI.return_error(e)
        except FileSystemException as e:
            self.logger.exception(
                '')  # Message is being handled by custom formatter
            imgr = ImageRepository()
            imgr.delete_with_name_from_project(node_name, self.project)
            time.sleep(30)
            self.haas.detach_node_from_project_network(node_name, network,
                                                       nic)
            return BMI.return_error(e)
        except DBException as e:
            self.logger.exception(
                '')  # Message is being handled by custom formatter
            time.sleep(30)
            self.haas.detach_node_from_project_network(node_name, network,
                                                       nic)
            return BMI.return_error(e)
        except HaaSException as e:
            self.logger.exception(
                '')  # Message is being handled by custom formatter
            return BMI.return_error(e)
        finally:
            self.logger.debug("Exiting Provision")

    # This is for detach a node and removing it from iscsi
    # and destroying its image
    def deprovision(self, node_name, network, nic):
        try:
            self.logger.debug("Entering Detach Node")
            self.logger.debug("Got parameters = %s %s %s", node_name, network, nic)

            self.logger.info("Detaching node %s from network %s", node_name,
                             network)
            self.haas.detach_node_from_project_network(node_name,
                                                       network, nic)
            self.logger.info("Successfully detached node %s from network %s",
                             node_name, network)

            with RBD(self.config.fs[
                         constants.CEPH_CONFIG_SECTION_NAME]) as fs:
                ceph_img_name = self.__get__ceph_image_name(node_name)
                ceph_config = self.config.fs[
                    constants.CEPH_CONFIG_SECTION_NAME]
                self.logger.debug("Contents of ceph+config = %s",
                                  str(ceph_config))
                self.logger.info(
                    "Calling ISCSI Shellscript with delete command")
                iscsi_output = BMI.__call_shellscript(
                    self.config.iscsi_update,
                    ceph_config[
                        constants.CEPH_KEY_RING_KEY],
                    ceph_config[
                        constants.CEPH_ID_KEY],
                    ceph_config[
                        constants.CEPH_POOL_KEY],
                    str(ceph_img_name),
                    constants.ISCSI_DELETE_COMMAND,
                    self.config.iscsi_update_password)
                self.logger.debug("Got Message from ISCSI Script = %s",iscsi_output)
                if constants.ISCSI_UPDATE_SUCCESS in iscsi_output[0]:
                    self.logger.info(
                        "The delete command was executed successfully")
                    self.logger.info("Removing Image %s", node_name)
                    imgr = ImageRepository()
                    imgr.delete_with_name_from_project(node_name,
                                                       self.project)
                    ret = fs.remove(str(ceph_img_name).encode("utf-8"))
                    self.logger.info("Successfully Removed Image %s", node_name)
                    return BMI.__return_success(ret)

                elif constants.ISCSI_UPDATE_FAILURE in iscsi_output[0]:
                    self.logger.debug("Raising Node Already Unmapped Exception")
                    raise iscsi_exceptions.NodeAlreadyUnmappedException()
        except (HaaSException, ISCSIException, FileSystemException, DBException) as e:
            self.logger.exception('')
            return BMI.return_error(e)
        finally:
            self.logger.debug("Exiting Detach Node")

    # Creates snapshot for the given image with snap_name as given name
    # fs_obj will be populated by decorator
    def create_snapshot(self, node_name, snap_name):
        try:
            self.logger.debug("Entered Create Snapshot")
            self.logger.debug("Got parameters = %s %s",node_name,snap_name)

            self.logger.info("Authenticating project %s", self.project)
            self.haas.validate_project(self.project)
            self.logger.info("Successfully Authenticated project %s",
                             self.project)

            self.logger.debug("Getting image id for image %s in project %s",
                              node_name, self.project)

            self.logger.debug("Getting image id for image %s in project %s",
                              node_name, self.project)
            ceph_img_name = self.__get__ceph_image_name(node_name)

            self.logger.debug("Got img_id = %s for image %s in project %s",
                             ceph_img_name, node_name, self.project)

            with RBD(self.config.fs[
                         constants.CEPH_CONFIG_SECTION_NAME]) as fs:
                fs.snap_image(ceph_img_name, constants.DEFAULT_SNAPSHOT_NAME)
                fs.snap_protect(ceph_img_name, constants.DEFAULT_SNAPSHOT_NAME)

                imgr = ImageRepository()
                imgr.insert(snap_name, self.pid, is_snapshot=True)

                snap_img_id = self.__get__ceph_image_name(snap_name)
                fs.clone(ceph_img_name, constants.DEFAULT_SNAPSHOT_NAME,
                         snap_img_id)
                fs.flatten(snap_img_id)
                fs.snap_image(snap_img_id, constants.DEFAULT_SNAPSHOT_NAME)
                fs.snap_protect(snap_img_id, constants.DEFAULT_SNAPSHOT_NAME)

                fs.snap_unprotect(ceph_img_name,
                                  constants.DEFAULT_SNAPSHOT_NAME)
                fs.remove_snapshots(ceph_img_name,
                                    constants.DEFAULT_SNAPSHOT_NAME)
                return BMI.__return_success(True)

        except (HaaSException, DBException, FileSystemException) as e:
            self.logger.exception('')
            return BMI.return_error(e)
        finally:
            self.logger.debug("Exiting Create Snapshot")

    # Lists snapshot for the given image img_name
    # URL's have to be read from BMI config file
    # fs_obj will be populated by decorator
    def list_snapshots(self):
        try:
            self.logger.debug("Entered List Snapshots")
            self.logger.debug("No parameters")

            self.logger.info("Authenticating project %s", self.project)
            self.haas.validate_project(self.project)
            self.logger.info("Successfully Authenticated project %s",
                             self.project)

            imgr = ImageRepository()
            return BMI.__return_success(
                imgr.fetch_snapshots_from_project(self.project))

        except (HaaSException, DBException, FileSystemException) as e:
            self.logger.exception('')
            return BMI.return_error(e)
        finally:
            self.logger.debug("Exiting List Snapshots")

    # Removes snapshot snap_name for the given image img_name
    # fs_obj will be populated by decorator
    def remove_image(self, img_name):
        try:
            self.logger.debug("Entered Remove Snaps")
            self.logger.debug("Got parameters = %s", img_name)

            self.logger.info("Authenticating project %s", self.project)
            self.haas.validate_project(self.project)

            self.logger.info("Successfully Authenticated project %s",
                             self.project)

            self.logger.debug("Getting image id for image %s in project %s",
                              img_name, self.project)
            ceph_img_name = self.__get__ceph_image_name(img_name)

            self.logger.debug("Got img_id = %s for image %s in project %s",
                              ceph_img_name, img_name, self.project)

            with RBD(self.config.fs[
                         constants.CEPH_CONFIG_SECTION_NAME]) as fs:
                fs.snap_unprotect(ceph_img_name,
                                  constants.DEFAULT_SNAPSHOT_NAME)
                fs.remove_snapshots(ceph_img_name,
                                    constants.DEFAULT_SNAPSHOT_NAME)
                fs.remove(ceph_img_name)
                imgr = ImageRepository()
                imgr.delete_with_name_from_project(
                    imgr.fetch_name_with_id(ceph_img_name[3:]),
                    self.project)
                return BMI.__return_success(True)
        except (HaaSException, DBException, FileSystemException) as e:
            self.logger.exception('')
            return BMI.return_error(e)
        finally:
            self.logger.debug("Exiting Remove Snaps")

    # Lists the images for the project which includes the snapshot
    def list_images(self):
        try:

            self.logger.debug("Entered List All Images")
            self.logger.debug("Got parameters = %s", self.project)

            self.logger.info("Authenticating project %s", self.project)
            self.haas.validate_project(self.project)
            self.logger.info("Successfully Authenticated project %s",
                             self.project)

            imgr = ImageRepository()
            self.logger.info("Fetching names from db for project %s",
                             self.project)
            names = imgr.fetch_images_from_project(self.project)
            self.logger.info("Got names successfully from db for project %s",
                             project)
            self.logger.debug("Names = %s", str(names))
            return BMI.__return_success(names)

        except (HaaSException, DBException) as e:
            self.logger.exception('')
            return BMI.return_error(e)
        finally:
            self.logger.debug("Exiting List All Images")