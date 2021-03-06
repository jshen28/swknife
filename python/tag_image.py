#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import subprocess,re
import datetime
from keystoneauth1 import loading, session

# Global variables
from glanceclient import Client
import os
import xlwt,xlrd
from xlrd import open_workbook


MAX_COLUMNS = 4
COLUME_NAME = ["index","image_uuid", "image_name", "image_tags"]
T = datetime.date.today()
INPUT_FILE = "swknife_collect.xlsx"

AUTH_URL='http://192.168.2.10:35357/v3'
USERNAME = 'admin'
PASSWORD = '89rqdHLMN5rm0x1P'
PROJECT_NAME = 'admin'
DOMAIN_NAME = 'Default'
DOMAIN_ID = 'default'
GLANCE_URL='http://192.168.2.10:9292'

def get_glance_client():
    loader = loading.get_plugin_loader('password')
    auth = loader.load_from_options(auth_url=AUTH_URL,
                                    username=USERNAME,
                                    password=PASSWORD,
                                    project_name=PROJECT_NAME,
                                    user_domain_name=DOMAIN_NAME,
                                    project_domain_name=DOMAIN_NAME)
    sess = session.Session(auth=auth)
    return Client('2',endpoint=GLANCE_URL,session=sess)

def tag_to_image(sheet):
    # ignore the first row
    for row in range(1, sheet.nrows):
        args = {}
        for col in range(sheet.ncols):

            # there should not be more than defined
            # number of columns
            if col > MAX_COLUMNS:
                break

            val = sheet.cell(row, col).value
            args[COLUME_NAME[col]] = val

        #logger.info("args: %s", str(args))
        print("args:%s" %args)
        image_id = args.get('image_uuid').strip()
        #already exist image tags
        old_tags = get_image_tags(image_id)
        if old_tags is None:
            print("The image:%s,not found" % (image_id))
        else:
        #set image tags
            for tag in args.get('image_tags').split(','):
                if len(old_tags) == 0:
                    update_image_tags(image_id,tag)
                else:
                    for old_tag in old_tags:
                        if tag == old_tag:
                            print("The image:%s,has the tag:%s" %( image_id,tag))
                        else:
                            update_image_tags(image_id, tag)
                            print("The image:%s,add the new tag:%s" % (image_id, tag))
#create xlsx
def build_sheet():
    style0 = xlwt.easyxf('font: name Times New Roman, color-index green, bold on',
                         num_format_str='#,##0')
    style1 = xlwt.easyxf('font: name Times New Roman, color-index black',
                         num_format_str='#,##0')

    wb = xlwt.Workbook()
    ws = wb.add_sheet('images')

    # First row
    for col in range(len(COLUME_NAME)):
        ws.write(0, col, COLUME_NAME[col], style0)

    return wb, ws, style1

def output_one_tags(wb, ws, style,index,image_uuid, image_name, image_tags):

    ws.write(index, 0, index, style)
    ws.write(index, 1, image_uuid, style)
    ws.write(index, 2, image_name, style)
    ws.write(index, 3, image_tags, style)

    wb.save('export_tag_images-'+T.strftime('%Y-%m-%d')+'.xls')

def write_all_tags(sheet):
    glance_client = get_glance_client()
    print("export all set images tags................")
    # ignore the first row
    wb, ws, style = build_sheet()
    index = 1
    for row in range(1, sheet.nrows):
        args = {}
        for col in range(sheet.ncols):

            # there should not be more than defined
            # number of columns
            if col > MAX_COLUMNS:
                break
            val = sheet.cell(row, col).value
            args[COLUME_NAME[col]] = val
        image_uuid = args.get('image_uuid').strip()
        if  get_image_tags(image_uuid) is None:
            print("image:%s not exist" % image_uuid)
            image_tags="None"
            image_name = args.get('image_name')
        else:
            image_tags = ','.join(get_image_tags(image_uuid))
            image_name = glance_client.images.get(image_uuid).name

        output_one_tags(wb, ws, style, index, image_uuid, image_name, image_tags)
        print("export image,uuid: %s,name:%s,tags:%s successful." %(image_uuid, image_name, image_tags))
        index +=1
    print("export set images tags file:"+"export_tag_images-"+T.strftime('%Y-%m-%d')+".xls"+" successful.")

def get_images():
    glance_client = get_glance_client()
    all_images = glance_client.images.list()
    #images object
    #return all_images
    for image in all_images:
        print( image.id,image.name,image.status,image.tags)

def get_id_byname(image_name):
    #by image name obtain imageid,exist the same name images
    image_id_list=[]
    glance_client = get_glance_client()
    all_images = glance_client.images.list()
    for image in all_images:
        if image.name == image_name:
            print("Image name:%s,id:%s" % (image_name,image.id))
            image_id_list.append(image.id)
    if len(image_id_list)== 0:
        print("Image name:%s,not found" % (image_name))
    return  image_id_list


def get_image_tags(image_id):
    glance_client = get_glance_client()
    try:
        image_tags = glance_client.images.get(image_id).get('tags')
        print("image:%s ,tag info:%s " % (image_id, image_tags))
        return image_tags
    except Exception:
        print("Could not find image resource:%s" % image_id)
        return None


def update_image_tags(image_id,tag_name):
    #set image tags
    glance_client = get_glance_client()
    try:
        glance_client.image_tags.update(image_id,tag_name)
        print("set image:%s ,tag:%s successful" % (image_id,tag_name))
    except Exception:
        print("set image:%s ,tag:%s failure" % (image_id,tag_name))

def delete_image_tags(image_id,tag_name):
    #delete image tags
    glance_client = get_glance_client()
    try:
        glance_client.image_tags.delete(image_id,tag_name)
        print("delete image:%s ,tag:%s successful" % (image_id,tag_name))
    except Exception:
        print("delete image:%s ,tag:%s failure" % (image_id,tag_name))

def get_parse():
    import argparse
    parser = argparse.ArgumentParser(description="parses information:")
    parser.add_argument('-i', '--input', dest='conf_path', help='Input images information excel file path.',
                        default=INPUT_FILE)
    return parser.parse_args()


def read_conf(file=INPUT_FILE):
    if os.path.exists(file):
        readbook = xlrd.open_workbook(file)
        return readbook
    else:
        print "Error: Config File:" + file + " is not existed."
        return None

def main():
    params = get_parse()

    workbook = read_conf(file=params.conf_path)
    if not workbook:
        print "Error: Please input correct config file path."
        raise Exception("path: %s does not exist!", params.conf_path)

    #get excel sheet data
    rsheet = workbook.sheet_by_name("tag_images")
    #add tag
    tag_to_image(rsheet)
    #export tag
    write_all_tags(rsheet)
    return 0


if __name__ == "__main__":
    exit(main())
