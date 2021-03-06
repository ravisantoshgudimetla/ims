#! /bin/python
import os
from contextlib import contextmanager

import constants
import rados
import rbd
from exception import *


# Need to think if there is a better way to reduce boilerplate exception
# handling code in methods

class RBD:
    def __init__(self, config):
        self.__validate(config)
        self.cluster = self.__init_cluster()
        self.context = self.__init_context()
        self.rbd = rbd.RBD()

    def __enter__(self):
        self.rbd = rbd.RBD()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tear_down()

    def __repr__(self):
        return str([self.rid, self.r_conf, self.pool])

    def __str__(self):
        return 'rid = {0}, conf_file = {1}, pool = {2},' \
               'current images {3}' \
            .format(self.rid, self.r_conf,
                    self.pool)

    # Validates the config arguments passed
    # If all are present then the values are copied to variables
    def __validate(self, config):
        try:
            self.rid = config[constants.CEPH_ID_KEY]
            self.r_conf = config[constants.CEPH_CONFIG_FILE_KEY]
            self.pool = config[constants.CEPH_POOL_KEY]
        except KeyError as e:
            raise file_system_exceptions.MissingConfigArgumentException(
                e.args[0])

        if not os.path.isfile(self.r_conf):
            raise file_system_exceptions.InvalidConfigArgumentException(
                constants.CEPH_CONFIG_FILE_KEY)

    def __init_context(self):
        return self.cluster.open_ioctx(self.pool.encode('utf-8'))

    def __init_cluster(self):
        cluster = rados.Rados(rados_id=self.rid, conffile=self.r_conf)
        cluster.connect()
        return cluster

    # Written to use 'with' for opening and closing images
    # Passing context as it is outside class
    # Need to see if it is ok to put it inside the class
    @contextmanager
    def __open_image(self, img_name):
        img = None
        try:
            img = rbd.Image(self.context, img_name)
            yield (img)
        finally:
            if img is not None:
                img.close()

    def tear_down(self):
        self.context.close()
        self.cluster.shutdown()

    # RBD Operations Section
    def list_images(self):
        return self.rbd.list(self.context)

    def create_image(self, img_id, img_size):
        try:
            self.rbd.create(self.context, img_id, img_size)
            return True
        except rbd.ImageExists:
            raise file_system_exceptions.ImageExistsException(img_id)
        except rbd.FunctionNotSupported:
            raise file_system_exceptions.FunctionNotSupportedException()

    def clone(self, parent_img_name, parent_snap_name, clone_img_name):
        try:
            parent_context = child_context = self.context
            self.rbd.clone(parent_context, parent_img_name, parent_snap_name,
                           child_context, clone_img_name, features=1)
            return True
        except rbd.ImageNotFound:
            # Can be raised if the img or snap is not found
            if parent_img_name not in self.list_images():
                img_name = parent_img_name
            else:
                img_name = parent_snap_name
            raise file_system_exceptions.ImageNotFoundException(img_name)
        except rbd.ImageExists:
            raise file_system_exceptions.ImageExistsException(clone_img_name)
        # No Clue when will this be raised so not testing
        except rbd.FunctionNotSupported:
            raise file_system_exceptions.FunctionNotSupportedException()
        # No Clue when will this be raised so not testing
        except rbd.ArgumentOutOfRange:
            raise file_system_exceptions.ArgumentsOutOfRangeException()

    def remove(self, img_id):
        try:
            self.rbd.remove(self.context, img_id)
            return True
        except rbd.ImageNotFound:
            raise file_system_exceptions.ImageNotFoundException(img_id)
        # Don't know how to raise this
        except rbd.ImageBusy:
            raise file_system_exceptions.ImageBusyException(img_id)
        # Forgot to test this
        except rbd.ImageHasSnapshots:
            raise file_system_exceptions.ImageHasSnapshotException(img_id)

    def write(self, img_id, data, offset):
        try:
            with self.__open_image(img_id) as img:
                img.write(data, offset)
        except rbd.ImageNotFound:
            raise file_system_exceptions.ImageNotFoundException(img_id)

    def snap_image(self, img_id, name):
        try:
            # Work around for Ceph problem
            snaps = self.list_snapshots(img_id)
            if name in snaps:
                raise file_system_exceptions.ImageExistsException(name)

            with self.__open_image(img_id) as img:
                img.create_snap(name)
                return True
        # Was having issue with ceph implemented work around (stack dump issue)
        except rbd.ImageExists:
            raise file_system_exceptions.ImageExistsException(img_id)
        except rbd.ImageNotFound:
            raise file_system_exceptions.ImageNotFoundException(img_id)

    def list_snapshots(self, img_id):
        try:
            with self.__open_image(img_id) as img:
                return [snap['name'] for snap in img.list_snaps()]
        except rbd.ImageNotFound:
            raise file_system_exceptions.ImageNotFoundException(img_id)

    def remove_snapshots(self, img_id, name):
        try:
            with self.__open_image(img_id) as img:
                img.remove_snap(name)
                return True
        except rbd.ImageNotFound:
            raise file_system_exceptions.ImageNotFoundException(img_id)
        # Don't know how to raise this
        except rbd.ImageBusy:
            raise file_system_exceptions.ImageBusyException(img_id)

    def get_image(self, img_id):
        try:
            return rbd.Image(self.context, img_id)
        except rbd.ImageNotFound:
            raise file_system_exceptions.ImageNotFoundException(img_id)
