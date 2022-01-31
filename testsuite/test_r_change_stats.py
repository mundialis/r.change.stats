#!/usr/bin/env python3

############################################################################
#
# MODULE:       r.change.stats test
# AUTHOR(S):    Guido Riembauer <riembauer at mundialis.de>
# PURPOSE:      Tests r.change.stats using actinia-test-assets
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

import csv
import os

from grass.gunittest.case import TestCase
from grass.gunittest.main import test
from grass.gunittest.gmodules import SimpleModule
import grass.script as gscript


class TestRChangeStats(TestCase):
    pid_str = str(os.getpid())
    landuse_map1 = "landuse96_28m_subset"
    landuse_map2 = "landuse96_28m_subset_flipped_%s" % pid_str
    result_cd = "landuse96_28m_subset_CD_%s" % pid_str
    reference_cd = "landuse96_28m_subset_CD_REF"
    reference_stats_file = "data/ref.csv"
    output_stats_file = gscript.tempfile()

    @classmethod
    def setUpClass(self):
        """Ensures expected computational region and generated data"""
        # set temp region
        self.use_temp_region()
        # set region to area
        self.runModule("g.region", raster=self.landuse_map1)
        self.runModule("g.extension", extension="r.flip")
        self.runModule("r.flip", input=self.landuse_map1, output=self.landuse_map2)
        self.runModule("r.category", map=self.landuse_map2, raster=self.landuse_map1)

    @classmethod
    def tearDownClass(self):
        """Remove the temporary region and generated data"""
        self.del_temp_region()
        self.runModule("g.remove", type="raster", name=self.landuse_map2, flags="f")

    def tearDown(self):
        """Remove the outputs created
        This is executed after each test run.
        """
        self.runModule("g.remove", type="raster", name=self.result_cd, flags="f")
        if os.path.isfile(self.output_stats_file):
            os.remove(self.output_stats_file)

    def test_changedetection_equals_reference(self):
        """Test if change detection raster equals reference"""

        r_change_stats_cd = SimpleModule(
            "r.change.stats",
            input="%s,%s" % (self.landuse_map1, self.landuse_map2),
            output=self.result_cd,
            window_size=3,
            flags="f",
        )
        self.assertModule(r_change_stats_cd)
        self.assertRasterExists(self.result_cd)
        # test that the result is the same as reference
        self.assertRastersNoDifference(
            self.result_cd, self.reference_cd, precision=0.0
        )

    def test_changedetection_stats_equal_reference(self):
        """Test if change detection stats equals reference"""

        r_change_stats_cd_csv = SimpleModule(
            "r.change.stats",
            input="%s,%s" % (self.landuse_map1, self.landuse_map2),
            output=self.result_cd,
            window_size=3,
            csv_path=self.output_stats_file,
            flags="fcl",
        )
        self.assertModule(r_change_stats_cd_csv)
        self.assertRasterExists(self.result_cd)
        self.assertFileExists(self.output_stats_file)
        # test that the result csv is the same as reference
        self.assertFilesEqualMd5(self.output_stats_file, self.reference_stats_file)

    def test_changedetection_stats_stdout(self):
        """Test if change detection stats to stdout equal reference"""

        r_change_stats_stdout = SimpleModule(
            "r.change.stats",
            input="%s,%s" % (self.landuse_map1, self.landuse_map2),
            output=self.result_cd,
            window_size=3,
            csv_path="-",
            flags="fcl",
        )
        self.assertModule(r_change_stats_stdout)
        self.assertRasterExists(self.result_cd)
        # test that the result stdout is equal to the reference
        ref_str = ""
        with open(self.reference_stats_file) as csvfile:
            reader = csv.reader(csvfile, delimiter="|")
            for row in reader:
                ref_str = ref_str + "|".join(row) + "\n"
        stdout = r_change_stats_stdout.outputs.stdout
        self.assertTrue(stdout)
        self.assertIn(ref_str, stdout)

    def test_changedetection_ignoreval(self):
        """Test if the ignore_value option works properly"""
        r_change_stats_ignore = SimpleModule(
            "r.change.stats",
            input="%s,%s" % (self.landuse_map1, self.landuse_map2),
            output=self.result_cd,
            window_size=3,
            ignore_value=10,
            csv_path="-",
            flags="fcl",
        )
        self.assertModule(r_change_stats_ignore)
        self.assertRasterExists(self.result_cd)
        stdout = r_change_stats_ignore.outputs.stdout
        self.assertTrue(stdout)
        ignore_str = "62|areas ignored (Mixed Hardwoods)|7.49%"
        self.assertIn(ignore_str, stdout)


if __name__ == "__main__":
    test()
