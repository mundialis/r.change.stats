## DESCRIPTION

*r.change.stats* is a GRASS GIS addon Python script to calculate changes
between two discrete raster maps, e.g. landcover classifications. It
takes only exactly two raster maps and calculates the change detection
based on the current region. The change map can be smoothened using a
mode filter by applying the **-f** flag and **window_size** parameter.
The output map contains category values for each combination of change
(from class X to class Y), which is indicated in the category labels. If
the **-l**flag is set, the category labels from the input raster maps
are used to describe the change in the output category labels. If the
**-c**flag is set, area statistics (in percentage of covered area) are
written to stdout or to a .csv file if indicated in the parameter
**csv_path**.

## EXAMPLE

```sh
r.change.stats input=classification_2016,classification_2020 output=change_2016_2020
# Computes a change map between both classifications, the resulting change map will be labelled according to input raster category values, e.g.
# 1002  Change from 20 to 10
# 1003  Change from 30 to 10
# ...

r.change.stats -flc input=classification_2016,classification_2020 output=change_2016_2020 window_size=9 csv_path=statistics.csv
# Computes a change map between both classifications, applies a mode fui the result, and saves area statistics of changed areas in a .csv file.
# Both resulting map and statistics are labelled according to labels of the input rasters, e.g.
# 1002 Change from low vegetation to forest 1.45%
# 1003 Change from water to forest 0.00%
# ...
```

## SEE ALSO

*[r.stats](https://grass.osgeo.org/grass-stable/manuals/r.stats.html),
[r.neighbors](https://grass.osgeo.org/grass-stable/manuals/r.neighbors.html),
[r.category](https://grass.osgeo.org/grass-stable/manuals/r.category.html),
[r.change.info](r.change.info.md) (addon)*

## AUTHOR

Guido Riembauer, [mundialis](https://www.mundialis.de/), Germany
