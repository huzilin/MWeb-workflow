# -*- coding: utf-8 -*-
"""Test

Usage:
  get_file.py <header>
  get_file.py tag [<tags>] [<header>]
  get_file.py (--help)
  get_file.py --version

Options:
  --version         Show version.
  tag <tags>        MWeb tags.
  header            Doc header.
"""
import sys
import pickle
import re
import os
import sqlite3
import string
import json

from docopt import docopt


def tag_promopt(cursor, tags, tags_string):
    if len(tags) == 0:
        sql = "select name from tag limit 10"
    elif tags_string[-1] == ",":
        sql = "select name from tag where"
        and_string = ""
        for tag in tags[:-1]:
            sql = " ".join([sql, and_string, "name not like '%s'" % tag])
            and_string = "and"
        sql = " ".join([sql, "limit 10"])
    elif tags_string[-1] == ".":
        sql = None
    else:
        sql = "select name from tag where name like '%s%%';" % tags[-1]

    if sql:
        cursor.execute(sql)
        return cursor.fetchall(), 1
    else:
        return None, 0


def output_tag(filtered_tags):
    if len(filtered_tags) == 0:
        print(json.dumps({"items": [{"title": "没有相关tag"}]}))
    else:
        output = {"items": []}
        autocomplete = ""
        for arg in sys.argv[1:]:
            autocomplete = " ".join([autocomplete, arg])

        for tag in filtered_tags:
            if sys.argv[-1] == "tag":
                autocomplete = " ".join([autocomplete, tag[0]])
            elif autocomplete.rfind(",") > autocomplete.rfind(" "):
                autocomplete = ",".join(
                    [autocomplete[:autocomplete.rfind(",")], tag[0]])
            else:
                autocomplete = " ".join(
                    [autocomplete[:autocomplete.rfind(" ")], tag[0]])
            output["items"].append(
                {"title": "tag: %s" % tag[0], "autocomplete": autocomplete[1:], "valid": "no"})
        print(json.dumps(output))


def get_tag_files(cursor, tags_string):
    tag_list = tags_string[:-1].split(",")

    tags = ""
    for each in tag_list:
        tags += '"%s",' % each
    tags = tags[:-1]

    sub_sql = 'select id from tag where name in (%s)' % tags

    sql = "SELECT a.aid||'.md' FROM tag_article a,article b WHERE a.aid=b.uuid AND a.rid IN (%s) GROUP BY a.aid HAVING count(1)>=%d ORDER BY b.dateModif desc;" % (
        sub_sql, len(tag_list))
    cursor.execute(sql)
    rst = cursor.fetchall()
    files = []
    for row in rst:
        files.append(row[0])
    return files


def header_promopt(header, files):
    docs_dir = "%s/docs" % MDOC_HOME
    doc2header = {}
    file_pattern = re.compile(r'.*\.md$')
    header_pattern = re.compile(r'%s' % header, re.I)
    if not files:
        docs = os.listdir(docs_dir)
    else:
        docs = files
    for doc in docs:
        if file_pattern.match(doc):
            doc_path = "%s/%s" % (docs_dir, doc)
            with open(doc_path, "rb") as f:
                line = f.readline()
                doc_header = str(line.decode("utf8", "ignore")).rstrip(
                    "\r\n").rstrip("\n").lstrip("# ").strip()
                if len(header) > 0:
                    if header_pattern.match(doc_header):
                        doc2header[doc_path] = doc_header
                else:
                    doc2header[doc_path] = doc_header
    return doc2header, 1


def output_header(doc2header):
    if len(doc2header) == 0:
        print(json.dumps({"items": [{"title": "没有相关header"}]}))
    else:
        output = {"items": []}
        for file, header in doc2header.items():
            output["items"].append(
                {"title": "header: %s" % header, "arg": file, "type": "file", "valid": "yes"})
        print(json.dumps(output))


if __name__ == '__main__':
    args = docopt(__doc__, help=False, version='MWeb workflow 1.0')
    tags = []
    tags_string = ""
    header = ""
    if args["--help"]:
        print(__doc__)
        sys.exit(0)

    if args["tag"] and args["<tags>"]:
        tags_string = args["<tags>"]
        tags = tags_string.split(",")
        tag_flag = 1
    else:
        tag_flag = 1

    if args["<header>"]:
        header = args["<header>"]

    f = open('MDOC_HOME', 'rb')
    MDOC_HOME = pickle.load(f)
    f.close

    if not MDOC_HOME:
        sys.exit(1)

    db = "%s/mainlib.db" % MDOC_HOME
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    files = []
    if tag_flag:
        filtered_tags, tag_flag = tag_promopt(cursor, tags, tags_string)
        if tag_flag:
            output_tag(filtered_tags)
            sys.exit(0)
        else:
            files = get_tag_files(cursor, tags_string)
    doc2header, header_flag = header_promopt(header, files)
    if header_flag:
        output_header(doc2header)
    conn.close()
