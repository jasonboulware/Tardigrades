#!/usr/bin/env python

import argparse
import os
import sys
import subprocess

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))

def update_commit_file():
    cmdline = ['git', 'rev-parse', '--short=8', 'HEAD']
    commit_id = subprocess.check_output(cmdline, cwd=ROOT_DIR).strip()
    print 'git commit: {}'.format(commit_id)
    with open(os.path.join(ROOT_DIR, 'commit.py'), 'w') as f:
        f.write("LAST_COMMIT_GUID = '{0}'\n".format(commit_id))

def run_docker_build(image_name, no_cache, dev):
    cmdline = ['docker', 'build', '--pull', '-t', image_name]
    if no_cache:
        cmdline.append('--no-cache')
    if dev:
        cmdline.extend(['--build-arg', 'DEV_INSTALL=1'])
    cmdline.append(ROOT_DIR)
    print 'running {}'.format(' '.join(cmdline))
    subprocess.check_call(cmdline)

def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-cache', action='store_true')
    parser.add_argument('--dev', action='store_true')
    parser.add_argument('image_name')
    return parser

def main(argv):
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:])
    update_commit_file()
    run_docker_build(args.image_name, args.no_cache, args.dev)

if __name__ == '__main__':
    main(sys.argv)
