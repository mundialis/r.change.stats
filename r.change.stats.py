#!/usr/bin/env python3

############################################################################
#
# MODULE:       r.change.stats
# AUTHOR(S):    Guido Riembauer <riembauer at mundialis.de>
# PURPOSE:      Calculates change statistics from two discrete raster maps
#
# COPYRIGHT:	(C) 2020-2022 by mundialis GmbH & Co. KG and the GRASS
#               Development Team
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#############################################################################

# %Module
# % description: Computes the pixelwise change from two input classifications. Optionally outputs spatial statistics of class changes calculated with r.stats.
# % keyword: raster
# % keyword: statistics
# % keyword: change detection
# % keyword: classification
# %end

# %option G_OPT_R_INPUTS
# % key: input
# % type: string
# % required: yes
# % multiple: yes
# % label: Names of the two input classification maps
# % description: Change will be computed from input map 1 to input map 2
# %end

# %option G_OPT_R_OUTPUT
# % key: output
# % type: string
# % required: yes
# % multiple: no
# % key_desc: name
# % description: Name for output raster map
# % gisprompt: new,cell,raster
# % guisection: Output
# %end

# %option
# % key: window_size
# % type: integer
# % required: no
# % multiple: no
# % label: Size of mode filter if -f flag is set
# % description: -f flag must be set
# %end

# %option G_OPT_F_OUTPUT
# % key: csv_path
# % type: string
# % required: no
# % multiple: no
# % label: Filename for output .csv-file (if omitted or "-" output to stdout).
# % description: -c flag must be set
# %end

# %option
# % key: ignore_value
# % type: integer
# % required: no
# % multiple: no
# % label: Raster value to be ignored in change detection
# % description: All changes to or from this value will be assigned the same value and visualised in white. useful for e.g. cloud masking
# %end

# %flag
# % key: f
# % description: Filter change detection product using a mode filter of size window_size
# %end

# %flag
# % key: c
# % description: Compute spatial statistics of class changes, optionally save them as a .csv-file
# %end

# %flag
# % key: l
# % description: Use raster labels for change detection statistics
# %end

# % rules
# % requires: window_size, -f
# % requires: csv_path, -c
# %end


import atexit
import csv
import numpy as np
import os
import grass.script as grass
from grass.lib.gis import GRASS_EPSILON

# initialize global vars
rm_rasters = []


def cleanup():
    nuldev = open(os.devnull, "w")
    kwargs = {"flags": "f", "quiet": True, "stderr": nuldev}
    for rmrast in rm_rasters:
        if grass.find_file(name=rmrast, element="raster")["file"]:
            grass.run_command("g.remove", type="raster", name=rmrast, **kwargs)


def reclassify(map_in, map_out, values_in, values_out):
    reclass_string = ""
    for idx, item in enumerate(values_in):
        reclass_string += "%s = %s\n" % (item, values_out[idx])
    recl = grass.feed_command("r.reclass", input=map_in, output=map_out, rules="-")
    recl.stdin.write(reclass_string.encode())
    recl.stdin.close()
    # feed_command does not wait until finished
    recl.wait()


def main():

    global rm_rasters

    # parameters
    input = options["input"].split(",")
    if len(input) != 2:
        grass.fatal(_("Input must consist of two raster maps"))
    output = options["output"]
    labels = flags["l"]
    if options["ignore_value"]:
        str_val = str(options["ignore_value"])
        ignore_label = None
        ignore_val_exists = False

    # get the category values and labels of the input maps
    cats_in1_tmp = list(
        grass.parse_command("r.category", map=input[0], separator="tab").keys()
    )
    cats_in1 = [cat.split("\t")[0] for cat in cats_in1_tmp]
    cats_in2_tmp = list(
        grass.parse_command("r.category", map=input[1], separator="tab").keys()
    )
    cats_in2 = [cat.split("\t")[0] for cat in cats_in2_tmp]
    if options["ignore_value"]:
        if str_val in cats_in1 or str_val in cats_in2:
            ignore_val_exists = True
        else:
            grass.warning(
                _("Value to ignore (%s) does not exist in input maps" % str_val)
            )

    if labels:
        try:
            labels_in1 = [cat.split("\t")[1] for cat in cats_in1_tmp]
            labels_in2 = [cat.split("\t")[1] for cat in cats_in2_tmp]
            labellist1 = [(cats_in1[idx], item) for idx, item in enumerate(labels_in1)]
            labellist2 = [(cats_in2[idx], item) for idx, item in enumerate(labels_in2)]
            labellist = list(set(labellist1 + labellist2))
            # check if cats and labels are unambiguous
            if len(set([tuple[1] for tuple in labellist])) != len(
                set([tuple[0] for tuple in labellist])
            ):
                grass.warning(
                    _(
                        "Input raster labels are ambiguous,"
                        + "using raster categories for result raster labels"
                    )
                )
                labels = False
            # get label of value to be ignored
            else:
                if options["ignore_value"] and ignore_val_exists is True:
                    ignore_label = [
                        item[1] for item in labellist if item[0] == str_val
                    ][0]

        except Exception:
            grass.warning(
                _(
                    "Input rasters are not (entirely) labelled,"
                    + " using raster categories for result raster labels"
                )
            )
            labels = False

    # get unique category values only
    all_cats = list(set(cats_in1 + cats_in2))
    all_cats.sort()

    # assign new category values
    new_cats = np.arange(1, len(all_cats) + 1, 1)
    new_cats_t1000 = [str(1000 * int(item)) for item in new_cats]

    # get new value to ignore
    if options["ignore_value"] and ignore_val_exists is True:
        ignore_idx = all_cats.index(str_val)
        new_ignore_val = new_cats[ignore_idx]

    # reclassify
    map1_recl = "map1_out_%s" % (os.getpid())
    map2_recl = "map2_out_%s" % (os.getpid())
    reclassify(input[0], map1_recl, all_cats, new_cats)
    reclassify(input[1], map2_recl, all_cats, new_cats_t1000)

    rm_rasters.append(map1_recl)
    rm_rasters.append(map2_recl)

    # calculate change detection map
    out_tmpname = "%s_%s" % (output, str(os.getpid()))
    rm_rasters.append(out_tmpname)
    grass.run_command(
        "r.mapcalc",
        expression="%s = if( abs(%s - %s) < %01.16f, 0, %s + %s)"
        % (out_tmpname, input[0], input[1], GRASS_EPSILON, map1_recl, map2_recl),
        quiet=True,
    )
    # filter
    out_tmpname2 = "%s_temp2_%s" % (output, str(os.getpid()))
    if flags["f"]:
        window_size = int(options["window_size"])
        grass.run_command(
            "r.neighbors",
            input=out_tmpname,
            output=out_tmpname2,
            size=window_size,
            method="mode",
            quiet=True,
        )
    else:
        grass.run_command(
            "g.rename", raster="%s,%s" % (out_tmpname, out_tmpname2), quiet=True
        )

    # get category values of change detection raster
    cats_cd_tmp = list(
        grass.parse_command("r.category", map=out_tmpname2, separator="tab").keys()
    )

    # put together rule string to label change detection map
    cd_labels = ["0:No Change"]
    cats_to_ignore = []
    for item in cats_cd_tmp:
        if item != "0":
            changed_from_reclass = int(item) % 1000
            changed_to_reclass = int((int(item) - changed_from_reclass) / 1000)
            if options["ignore_value"] and ignore_val_exists is True:
                if changed_from_reclass == int(
                    new_ignore_val
                ) or changed_to_reclass == int(new_ignore_val):
                    cats_to_ignore.append(item)
            changed_from = all_cats[
                [item for item in new_cats].index(changed_from_reclass)
            ]
            changed_to = all_cats[
                [item for item in new_cats].index(changed_to_reclass)
            ]
            if labels:
                labellist_classnum = [tuple[0] for tuple in labellist]
                labellist_classtext = [tuple[1] for tuple in labellist]
                changed_from_label = labellist_classtext[
                    labellist_classnum.index(changed_from)
                ]
                changed_to_label = labellist_classtext[
                    labellist_classnum.index(changed_to)
                ]
                changed_from = changed_from_label
                changed_to = changed_to_label
            cd_labels.append(
                "%s:Change from %s to %s" % (item, changed_from, changed_to)
            )
    category_text = "\n".join(cd_labels)

    # assign labels
    cat_proc = grass.feed_command(
        "r.category", map=out_tmpname2, rules="-", separator=":"
    )
    cat_proc.stdin.write(category_text.encode())
    cat_proc.stdin.close()
    # feed_command does not wait until finished
    cat_proc.wait()

    # get old values to be reclassified to small pixel values
    old_vals_labels = list(
        grass.parse_command("r.category", map=out_tmpname2, separator=":").keys()
    )
    old_vals = [str.split(":")[0] for str in old_vals_labels]
    old_labels = [str.split(":")[1] for str in old_vals_labels]
    out_vals = range(len(old_vals_labels))
    out_vals_labels = []
    for idx, out_val in enumerate(out_vals):
        out_vals_labels.append("%s  %s" % (out_val, old_labels[idx]))

    # create reclassified map
    reclassmap = "tmp_reclass_%s" % (str(os.getpid()))
    rm_rasters.append(reclassmap)
    # add out_tmpname2 after reclassmap, because it is a basemap
    rm_rasters.append(out_tmpname2)

    if options["ignore_value"] and ignore_val_exists is True:
        old_vals_ignore_idcs = [old_vals.index(cat) for cat in cats_to_ignore]
        ignore_out_cat = max(out_vals) + 10
        for index in old_vals_ignore_idcs:
            out_vals_labels[index] = "%d areas ignored" % ignore_out_cat
            if ignore_label:
                out_vals_labels[index] += " (%s)" % ignore_label

    reclassify(out_tmpname2, reclassmap, old_vals, out_vals_labels)
    # make reclassified map persistent
    grass.run_command("r.mapcalc", expression="%s = %s" % (output, reclassmap))

    # assign random colors to output map
    grass.run_command("r.colors", map=output, color="random", quiet=True)

    # visualise no change in grey, ignored areas in white
    colors_tmp = list(grass.parse_command("r.colors.out", map=output).keys())
    # r.colors.out does not show color for category 0
    colors_new = ["0 200:200:200"]
    for color_rule in colors_tmp:
        if options["ignore_value"] and ignore_val_exists is True:
            if color_rule.split(" ")[0] == str(ignore_out_cat):
                color_rule = "%s 250:250:250" % str(ignore_out_cat)
        colors_new.append(color_rule)
    color_str = "\n".join(colors_new)
    col_proc = grass.feed_command("r.colors", map=output, rules="-", quiet=True)
    col_proc.stdin.write(color_str.encode())
    col_proc.stdin.close()
    col_proc.wait()

    # calculate statistics and export .csv
    headerline = ["raster value|label|percentage of covered area"]
    if flags["c"]:
        kwargs = {"input": output, "separator": "pipe", "flags": "lp"}
        if options["csv_path"] and options["csv_path"] != "-":
            kwargs["output"] = options["csv_path"]
            grass.run_command("r.stats", **kwargs, quiet=True)
        else:
            # print header to stdout too
            outstr = grass.read_command("r.stats", **kwargs, quiet=True)
            print("%s\n%s" % (headerline[0], outstr))

    grass.message(_("Generated output map <%s>" % (output)))
    if options["csv_path"] and options["csv_path"] != "-":
        # add header line
        csvfile = options["csv_path"]
        with open(csvfile, "r") as infile:
            reader = list(csv.reader(infile))
            reader.insert(0, headerline)
        with open(csvfile, "w") as outfile:
            writer = csv.writer(outfile, lineterminator="\n")
            for line in reader:
                writer.writerow(line)
        grass.message(_("Change statistics written to file <%s>" % (csvfile)))


if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()
