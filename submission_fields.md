# NPDC Data Submission Fields Documentation

Below is a comprehensive list of all data fields that users must fill out during the NPDC dataset submission process, along with their database data types and maximum length constraints.

---

## 1. Primary Dataset Fields (`DatasetSubmission`)

| Field Name | Data Type | Max Length | Notes |
| :--- | :--- | :--- | :--- |
| **Metadata ID** | Text (`CharField`) | 50 | Auto-generated standard identifier |
| **Title** | Text (`CharField`) | 500 | |
| **Abstract** | Text (`TextField`) | 1000 | |
| **Purpose** | Text (`TextField`) | 1000 | |
| **Version** | Text (`CharField`) | 50 | Defaults to "1.0" |
| **Keywords** | Text (`TextField`) | 1000 | Comma-separated internally |
| **Expedition Type** | Dropdown (`CharField`) | 30 | Options: Antarctic, Arctic, Southern Ocean, Himalaya |
| **Expedition Year** | Dropdown (`CharField`) | 9 | Generated dynamically |
| **Expedition Number** | Number string (`CharField`) | 100 | Restricted to digits on frontend |
| **Project Number** | Number string (`CharField`) | 100 | Restricted to digits on frontend |
| **Project Name** | Text (`CharField`) | 500 | |
| **Category** | Dropdown (`CharField`) | 50 | Predefined science categories |
| **ISO Topic** | Dropdown (`CharField`) | 100 | Predefined ISO metadata topics |
| **Data Set Progress** | Dropdown (`CharField`) | 20 | Options: Planned, In Work, Complete |
| **Access Constraints** | Text (`TextField`) | None | |
| **Use Constraints** | Text (`TextField`) | None | |
| **Data Set Language** | Text (`CharField`) | 100 | default `eng` |
| **Distribution Media** | Text (`CharField`) | 200 | |
| **Distribution Format** | Text (`CharField`) | 100 | |
| **Distribution Size** | Text (`CharField`) | 100 | |

---

## 2. Spatial & Temporal Coverage

| Field Name | Data Type | Max Length | Range / Notes |
| :--- | :--- | :--- | :--- |
| **Temporal Start Date** | Date (`DateField`) | - | |
| **Temporal End Date** | Date (`DateField`) | - | |
| **West Longitude** | Decimal (`FloatField`) | - | -180 to 180 |
| **East Longitude** | Decimal (`FloatField`) | - | -180 to 180 |
| **South Latitude** | Decimal (`FloatField`) | - | -90 to 90 |
| **North Latitude** | Decimal (`FloatField`) | - | -90 to 90 |

---

## 3. Dataset Citation

| Field Name | Data Type | Max Length |
| :--- | :--- | :--- |
| **Creator** | Text (`CharField`) | 500 |
| **Editor** | Text (`CharField`) | 500 |
| **Title** | Text (`CharField`) | 500 |
| **Series Name** | Text (`CharField`) | 500 |
| **Release Date** | Date (`DateField`) | - |
| **Release Place** | Text (`CharField`) | 500 |
| **Version** | Text (`CharField`) | 50 |
| **Online Resource** | URL/Text (`CharField`) | 1000 |

---

## 4. Scientist Details

| Field Name | Data Type | Max Length | Notes |
| :--- | :--- | :--- | :--- |
| **Role** | Dropdown (`CharField`) | 100 | |
| **Title** | Text (`CharField`) | 50 | E.g., Dr., Prof., Mr. |
| **First Name** | Text (`CharField`) | 100 | |
| **Middle Name** | Text (`CharField`) | 100 | |
| **Last Name** | Text (`CharField`) | 100 | |
| **Email** | Email (`EmailField`) | 254 | Strict email formatting enforced |
| **Institute** | Text (`CharField`) | 500 | |
| **Address** | Text (`CharField`) | 500 | |
| **City** | Text (`CharField`) | 500 | |
| **State** | Text (`CharField`) | 500 | |
| **Country** | Choice (`CharField`) | 500 | Restricted via django-countries logic |
| **Phone** | Numbers/Text (`CharField`) | 25 | Standardized length up to 25 to support International formatting (+1 max digits) |
| **Mobile** | Numbers/Text (`CharField`) | 25 | Standardized length up to 25 to support International formatting (+1 max digits) |
| **Postal Code** | Numbers (`CharField`) | 6 | Strictly restricted to exactly 6 digits |

---

## 5. Instrument & Platform Metadata

| Category | Field Name | Data Type | Max Length |
| :--- | :--- | :--- | :--- |
| **Instrument** | Short Name | Text (`CharField`) | 100 |
| **Instrument** | Long Name | Text (`CharField`) | 200 |
| **Platform** | Short Name | Text (`CharField`) | 100 |
| **Platform** | Long Name | Text (`CharField`) | 200 |

---

## 6. Location & GPS Metadata

| Field Name | Data Type | Max Length | Notes |
| :--- | :--- | :--- | :--- |
| **Location Category** | Text (`CharField`) | 100 | |
| **Location Type** | Text (`CharField`) | 100 | Auto-detected from expedition type |
| **Location Subregion** | Choice (`CharField`) | 100 | E.g., Bharati, Maitri |
| **Other Subregion** | Text (`CharField`) | 100 | |
| **GPS Used?** | Boolean (`BooleanField`) | - | |
| **Minimum Altitude** | Decimal (`FloatField`) | - | Restricted to numbers & decimals |
| **Maximum Altitude** | Decimal (`FloatField`) | - | Restricted to numbers & decimals |
| **Minimum Depth** | Decimal (`FloatField`) | - | Restricted to numbers & decimals |
| **Maximum Depth** | Decimal (`FloatField`) | - | Restricted to numbers & decimals |

---

## 7. Data Resolution & Paleo-Temporal Coverage

| Category | Field Name | Data Type | Max Length |
| :--- | :--- | :--- | :--- |
| **Resolution** | Latitude Resolution | Text (`CharField`) | 100 |
| **Resolution** | Longitude Resolution | Text (`CharField`) | 100 |
| **Resolution** | Horizontal Res Range | Choice (`CharField`) | 100 |
| **Resolution** | Vertical Resolution | Text (`CharField`) | 100 |
| **Resolution** | Vertical Res Range | Choice (`CharField`) | 100 |
| **Resolution** | Temporal Resolution | Text (`CharField`) | 100 |
| **Resolution** | Temporal Res Range | Choice (`CharField`) | 100 |
| **Paleo-Temporal** | Start Date | Date (`DateField`) | - |
| **Paleo-Temporal** | Stop Date | Date (`DateField`) | - |
| **Paleo-Temporal** | Chronostratigraphic Unit | Text (`CharField`) | 255 |

---

## 8. Upload Fields

| Field Name | Data Type | Restrictions |
| :--- | :--- | :--- |
| **Data File** | File (`FileField`) | Max size 500MB, rejected execution extensions (exe, sh, js, etc.) |
| **Metadata File** | File (`FileField`) | - |
| **Readme File** | File (`FileField`) | - |
