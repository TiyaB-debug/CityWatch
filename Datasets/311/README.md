# NYC 311 service requests

[NYC Open Data source](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data)

The CityWatch window is January 1, 2023 through November 7, 2026, inclusive, using the service request's creation date. The source reported 13,728,419 matching requests on November 7, 2026. The latest available request at that check was dated November 6, 2026. Counts and records may change as NYC updates the dataset.

From this directory, run with Python 3.10 or later:

```sh
python3 download_311.py
```

The script retrieves all source columns and writes weekly CSV gzip files to `exports/`. It checks each week's row count against the API and checks for duplicate request IDs within that week. The full export is large and the download may take a while. The exported files are stored locally. To retrieve a smaller window, pass inclusive dates:

```sh
python3 download_311.py --start 2023-01-01 --end 2023-01-07
```
