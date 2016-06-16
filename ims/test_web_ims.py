import time
import unittest

import requests

import ims.common.constants as constants

url = "http://192.168.122.125:8000/"

CORRECT_HAAS_USERNAME = "haasadmin"
CORRECT_HAAS_PASSWORD = "admin1234"
INCORRECT_HAAS_PASSWORD = "admin123##"

NODE_NAME = "cisco-27"
CHANNEL = "vlan/native"
NIC = "enp130s0f0"

PROJECT = "bmi_infra"
WRONG_PROJECT = "bmi_infr"
NETWORK = "bmi-provision"

EXIST_IMG_NAME = "hadoopMaster.img"
EXIST_SNAP_NAME = "HadoopMasterGoldenImage"
NOT_EXIST_IMG_NAME = "i12"
NOT_EXIST_SNAP_NAME = "hello"

NEW_SNAP_NAME = "blblb1"  # for creating snapshot



class TestOperations(unittest.TestCase):
    def test_provision(self):
        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.NODE_NAME_PARAMETER: NODE_NAME,
                constants.IMAGE_NAME_PARAMETER: NOT_EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: EXIST_SNAP_NAME,
                constants.NETWORK_PARAMETER: NETWORK,
                constants.CHANNEL_PARAMETER: CHANNEL,
                constants.NIC_PARAMETER: NIC}
        res = requests.put(url + "provision_node/", data=data,
                           auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 404)

        time.sleep(30)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.NODE_NAME_PARAMETER: NODE_NAME,
                constants.IMAGE_NAME_PARAMETER: EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: NOT_EXIST_SNAP_NAME,
                constants.NETWORK_PARAMETER: NETWORK,
                constants.CHANNEL_PARAMETER: CHANNEL,
                constants.NIC_PARAMETER: NIC}
        res = requests.put(url + "provision_node/", data=data,
                           auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 404)

        time.sleep(30)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.NODE_NAME_PARAMETER: NODE_NAME,
                constants.IMAGE_NAME_PARAMETER: EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: EXIST_SNAP_NAME,
                constants.NETWORK_PARAMETER: NETWORK,
                constants.CHANNEL_PARAMETER: CHANNEL,
                constants.NIC_PARAMETER: NIC}
        res = requests.put(url + "provision_node/", data=data,
                           auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 200)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.NODE_NAME_PARAMETER: NODE_NAME,
                constants.IMAGE_NAME_PARAMETER: NOT_EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: EXIST_SNAP_NAME,
                constants.NETWORK_PARAMETER: NETWORK,
                constants.CHANNEL_PARAMETER: CHANNEL,
                constants.NIC_PARAMETER: NIC}
        res = requests.put(url + "provision_node/", data=data,
                           auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 500)

        time.sleep(30)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.NODE_NAME_PARAMETER: NODE_NAME,
                constants.IMAGE_NAME_PARAMETER: NOT_EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: EXIST_SNAP_NAME,
                constants.NETWORK_PARAMETER: NETWORK,
                constants.CHANNEL_PARAMETER: CHANNEL,
                constants.NIC_PARAMETER: NIC}
        res = requests.put(url + "provision_node/", data=data,
                           auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 500)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.NODE_NAME_PARAMETER: NODE_NAME,
                constants.NETWORK_PARAMETER: NETWORK,
                constants.NIC_PARAMETER: NIC}
        res = requests.delete(url + "remove_node/", data=data, auth=(
            CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 200)

        print ""
        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.NODE_NAME_PARAMETER: NODE_NAME,
                constants.NETWORK_PARAMETER: NETWORK,
                constants.NIC_PARAMETER: NIC}
        res = requests.delete(url + "remove_node/", data=data, auth=(
            CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 500)

    def test_create_snapshot(self):
        print "create snapshot"

        data = {constants.PROJECT_PARAMETER: WRONG_PROJECT,
                constants.IMAGE_NAME_PARAMETER: EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: NEW_SNAP_NAME}
        res = requests.put(url + "snap_image/", data=data,
                           auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 404)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.IMAGE_NAME_PARAMETER: NOT_EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: NEW_SNAP_NAME}
        res = requests.put(url + "snap_image/", data=data,
                           auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 404)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.IMAGE_NAME_PARAMETER: EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: NEW_SNAP_NAME}
        res = requests.put(url + "snap_image/", data=data,
                           auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 200)

        print "list snapshots"

        data = {constants.PROJECT_PARAMETER: WRONG_PROJECT,
                constants.IMAGE_NAME_PARAMETER: EXIST_IMG_NAME}
        res = requests.post(url + "list_snapshots/", data=data,
                            auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 404)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.IMAGE_NAME_PARAMETER: NOT_EXIST_IMG_NAME}
        res = requests.post(url + "list_snapshots/", data=data,
                            auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 404)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.IMAGE_NAME_PARAMETER: EXIST_IMG_NAME}
        res = requests.post(url + "list_snapshots/", data=data,
                            auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        js = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(js[-1], NEW_SNAP_NAME)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.IMAGE_NAME_PARAMETER: EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: NEW_SNAP_NAME}
        res = requests.put(url + "snap_image/", data=data,
                           auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 471)

        print "remove snapshots"

        data = {constants.PROJECT_PARAMETER: WRONG_PROJECT,
                constants.IMAGE_NAME_PARAMETER: EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: NEW_SNAP_NAME}
        res = requests.delete(url + "remove_snapshot/", data=data, auth=(
            CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 404)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.IMAGE_NAME_PARAMETER: NOT_EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: NEW_SNAP_NAME}
        res = requests.delete(url + "remove_snapshot/", data=data, auth=(
            CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 404)

        data = {constants.PROJECT_PARAMETER: PROJECT,
                constants.IMAGE_NAME_PARAMETER: EXIST_IMG_NAME,
                constants.SNAP_NAME_PARAMETER: NEW_SNAP_NAME}
        res = requests.delete(url + "remove_snapshot/", data=data, auth=(
            CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 200)

    def test_list_all_images(self):
        data = {constants.PROJECT_PARAMETER: WRONG_PROJECT}
        res = requests.post(url + "list_images/", data=data,
                            auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        self.assertEqual(res.status_code, 404)

        data = {constants.PROJECT_PARAMETER: PROJECT}
        res = requests.post(url + "list_images/", data=data,
                            auth=(CORRECT_HAAS_USERNAME, CORRECT_HAAS_PASSWORD))
        print res.content
        js = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(js.__len__(), 2)
        self.assertEqual(js[0], NOT_EXIST_IMG_NAME)
        self.assertEqual(js[1], EXIST_IMG_NAME)