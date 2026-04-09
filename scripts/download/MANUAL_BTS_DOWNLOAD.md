# Manual BTS download (fallback)

Use this if `download_bts_data.py` fails (timeouts, blocking, or checkbox changes).

## On-Time — 12 monthly files

1. Open  
   https://www.transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ  
2. Uncheck **Prezipped File** only if you want a single CSV inside the ZIP unchanged; the automation leaves defaults.  
3. Uncheck **Select all variables**, then select only the fields listed under “On-Time Reporting” in `data/reference/field_selection_notes.md`.  
4. **Geography:** All. **Year:** 2025. **Period:** choose month 1–12.  
5. Click **Download**. Unzip; rename the CSV to `on_time_2025_MM.csv` and place it in `data/raw/on_time/2025/`.  
6. Repeat for each month. Do not skip months.

## T-100 Segment — 12 monthly files

1. Open  
   https://www.transtats.bts.gov/DL_SelectFields.asp?QO_fu146_anzr=&gnoyr_VQ=FMG  
2. Same pattern: select fields from `field_selection_notes.md` (T-100 table), **All** geography, **2025**, one **month** at a time, **Download**, unzip, save as `data/raw/t100_segment/2025/t100_2025_MM.csv`.

## Master Coordinate — one file

1. Open  
   https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=N8vn6v10&gnoyr_VQ=FLL  
2. Select Master Coordinate fields per `field_selection_notes.md`. There is no year/month filter.  
3. **Download**, unzip, save as `data/raw/airport_reference/master_coordinate_latest.csv`.

Then run `python scripts/download/verify_downloads.py --year 2025`.
