# Field selection notes (TranStats → spec)

BTS **DL_SelectFields** checkboxes use internal column names (`name` / `id` on the form). The downloader selects the following.

## On-Time Reporting (`on_time_2025_MM.csv`)

Inner CSV name from BTS is typically `T_ONTIME_REPORTING.csv`. Columns align with these checkboxes:

| Spec / prompt name | TranStats checkbox |
|-------------------|-------------------|
| Year | `YEAR` |
| Month | `MONTH` |
| FlightDate | `FL_DATE` |
| Reporting_Airline | `OP_UNIQUE_CARRIER` |
| DOT_ID_Reporting_Airline | `OP_CARRIER_AIRLINE_ID` |
| OriginAirportID | `ORIGIN_AIRPORT_ID` |
| Origin | `ORIGIN` |
| DestAirportID | `DEST_AIRPORT_ID` |
| Dest | `DEST` |
| CRSDepTime | `CRS_DEP_TIME` |
| DepTime | `DEP_TIME` |
| DepDelay | `DEP_DELAY` |
| CRSArrTime | `CRS_ARR_TIME` |
| ArrTime | `ARR_TIME` |
| ArrDelay | `ARR_DELAY` |
| Cancelled | `CANCELLED` |
| Diverted | `DIVERTED` |
| Distance | `DISTANCE` |

## Master Coordinate (`master_coordinate_latest.csv`)

| Spec / prompt name | TranStats checkbox |
|-------------------|-------------------|
| AirportSeqID | `AIRPORT_SEQ_ID` |
| AirportID | `AIRPORT_ID` |
| Airport | `AIRPORT` |
| AirportName | `DISPLAY_AIRPORT_NAME` |
| AirportCityName | `DISPLAY_AIRPORT_CITY_NAME_FULL` |
| AirportStateName | `AIRPORT_STATE_NAME` |
| AirportStateCode | `AIRPORT_STATE_CODE` |
| AirportCountryName | `AIRPORT_COUNTRY_NAME` |
| AirportCountryCodeISO | `AIRPORT_COUNTRY_CODE_ISO` |
| Latitude | `LATITUDE` |
| Longitude | `LONGITUDE` |
| UTCLocalTimeVariation | `UTC_LOCAL_TIME_VARIATION` |
| AirportIsClosed | `AIRPORT_IS_CLOSED` |
| AirportIsLatest | `AIRPORT_IS_LATEST` |

## T-100 Segment (`t100_2025_MM.csv`)

| Spec / prompt name | TranStats checkbox |
|-------------------|-------------------|
| Year | `YEAR` |
| Month | `MONTH` |
| OriginAirportID | `ORIGIN_AIRPORT_ID` |
| Origin | `ORIGIN` |
| DestAirportID | `DEST_AIRPORT_ID` |
| Dest | `DEST` |
| DepScheduled | `DEPARTURES_SCHEDULED` |
| DepPerformed | `DEPARTURES_PERFORMED` |
| Seats | `SEATS` |
| Passengers | `PASSENGERS` |
| Distance | `DISTANCE` |
| AirTime | `AIR_TIME` |
| RampToRamp | `RAMP_TO_RAMP` |

## Filters (ETL, not download)

- Keep rows where both `ORIGIN_AIRPORT_ID` and `DEST_AIRPORT_ID` map to **U.S.** airports per Master Coordinate country fields.
- Monthly snapshots; primary edge weight from flight counts (On-Time rows or aggregated T-100 `DEPARTURES_PERFORMED` depending on pipeline stage).
