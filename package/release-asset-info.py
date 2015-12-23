#!/usr/bin/python -B

import requests
import argparse
import os
import sys
import json

#-------------------------------------------------------------------------------
USAGE = "%(prog)s [-r <release_id> [-f]]"
DESC  = """
  Display/fix-up the 'label' names for downloadable assets attached to a release.\
"""

TAULABS_API_BASE = "https://api.github.com/repos/d-ronin/dRonin"

#-------------------------------------------------------------------------------
def main():
    # Setup the command line arguments.
    parser = argparse.ArgumentParser(usage = USAGE, description = DESC)

    parser.add_argument("-r", "--release_id",
                        action  = "store",
                        dest    = "release_id",
                        help    = "select the specified release by its ID.")

    parser.add_argument("-f", "--fixup-labels",
                        action  = "store_true",
                        default = False,
                        dest    = "fixup_labels",
                        help    = "fix the asset labels for the selected release.")

    # Parse the command-line.
    args = parser.parse_args()

    # Grab all info about releases
    releases_req = requests.get(TAULABS_API_BASE + '/releases')
    if releases_req.status_code != 200:
        print "Failed to enumerate valid releases"
        sys.exit(2)

    # Convert the results to json
    releases = releases_req.json()

    # Display a summary of the available releases
    print ""
    print "Available releases:"
    print "\t{0:8s} {1:20s} {2:22s} {3:s}".format("ID", "Name", "Published at", "Tag Name")
    for rel in releases:
        print "\t{id:8d} {name:20s} {published_at:22s} {tag_name:s}".format(**rel)

    if args.release_id is None:
        print "No selected release.  Exiting."
        sys.exit(0)

    # Make sure the selected release is one of the valid releases
    selected_rel = filter(lambda rel: rel['id'] == int(args.release_id), releases)
    if selected_rel is None:
        print "Requested release (%s) is not a valid release ID" % args.release_id
        sys.exit(2)
    selected_rel = selected_rel[0]

    # Fetch the list of assets for the selected release
    assets_req = requests.get(selected_rel['assets_url'])
    if assets_req.status_code != 200:
        print "Failed to retrieve assets for release '%s'" % args.fixup_release_id
        sys.exit(2)
    assets = assets_req.json()

    # Compute the new label for each asset according to the suffix on the file name
    for asset in assets:
        name = asset['name']
        if name.endswith('.apk'):
            label = "Android"
        elif name.endswith('_linux_i686.tar.xz'):
            label = "Linux 32-bit"
        elif name.endswith('.tar.xz'):
            label = "Linux 64-bit portable"
        elif name.endswith('.deb'):
            label = "Linux 64-bit Debian-style package"
        elif name.endswith('.zip'):
            label = "Windows (portable)"
        elif name.endswith('-install.exe'):
            label = "Windows (installer)"
        elif name.endswith('.dmg'):
            label = "Mac OS X"
        else:
            label = name
        asset['new_label'] = label

    # Display the available assets for the selected release
    print ""
    print "Available assets for selected release '{name:s}' ({id:d})".format(**selected_rel)
    print "\t{0:8s} {1:20s} {2:s}".format("ID", "Current Label", "New Label", "Name")
    for asset in assets:
        print "\t{id:8d} {label:20s} {new_label:20s} {name:s}".format(**asset)

    # Should we fix the asset labels?
    if args.fixup_labels is False:
        # We're done
        sys.exit(0)

    # We've been asked to fix up the asset labels.  Check all prerequisites.
    prereqs_valid = True

    # Make sure we have a github token to use
    if not "GITHUB_TOKEN" in os.environ:
        print "You must supply a valid GITHUB_TOKEN environment variable in order to update a release."
        prereqs_valid = False

    # Have all prerequisites been met?
    if not prereqs_valid:
        sys.exit(2)

    # Set the new label for each asset according to the suffix on the file name
    for asset in assets:
        print "Setting label to '{new_label:s}' for file named '{name:s}'".format(**asset)
        patch_req = requests.patch(asset['url'],
                                   data = json.dumps({ 'name' : asset['name'], 'label' : asset['new_label'] }),
                                   auth=("", os.environ['GITHUB_TOKEN']))
        if patch_req.status_code == 200:
            print "\t%d OK" % (patch_req.status_code)
        else:
            print "\t%d FAILED" % (patch_req.status_code)

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
