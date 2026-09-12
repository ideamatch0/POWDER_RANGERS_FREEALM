This readme file was generated on [2025-03-19] by [Zackary Snow]


GENERAL INFORMATION

1. Title of Dataset: In situ Visible Light and Thermal Imaging Data from a Laser Powder Bed Fusion Additive Manufacturing Process Co-Registered to X-ray Computed Tomography and Fatigue Data

2. Author Information
	A. Principal Investigator Contact Information
		Name: Zackary Snow
		ORCID: https://orcid.org/0000-0001-5901-6785
		Institution: Oak Ridge National Laboratory
		Address: 2350 Cherahala Blvd, Knoxville, TN 37932
		Email: snowzk@ornl.gov

	B. Associate or Co-investigator Contact Information
		Name: Luke Scime
		ORCID: https://orcid.org/0000-0002-0506-253X
		Institution: Oak Ridge National Laboratory
		Address: 2350 Cherahala Blvd, Knoxville, TN 37932
		Email: scimelr@ornl.gov

	C. Alternate Contact Information
		Name: Jeff Price
		ORCID: https://orcid.org/0009-0008-3955-9473
		Institution: Oak Ridge National Laboratory
		Address: 2350 Cherahala Blvd, Knoxville, TN 37932
		Email: pricejr@ornl.gov

3. Date of data collection: 2024-05-01 to 2024-05-05

4. Geographic location of data collection: Oak Ridge, TN

5. Information about funding sources that supported the collection of the data: 
This research was sponsored by the US Department of Energy’s Advanced Materials and Manufacturing Technologies Office. This dataset has been authored by UT-Battelle, LLC, under contract DE-AC05–00OR22725 with the U.S. Department of Energy (DOE).

SHARING/ACCESS INFORMATION

1. Reuse restrictions placed on the data: N/A

2. Links to publications that cite or use the data: N/A

3. Links to other publicly accessible locations of the data: N/A

4. Links/relationships to ancillary data sets: N/A

5. Was data derived from another source? If yes, list source(s): N/A

6. Recommended citation for this dataset: 
Z. Snow, L. Scime, C. Joslin, W. Halsey, A. Marquez Rossy, A. Ziabari, V. Paquit, R. Dehoff, "In situ Visible Light and Thermal Imaging Data from a Laser Powder Bed Fusion Additive Manufacturing Process Co-Registered to X-ray Computed Tomography and Fatigue Data", Oak Ridge National Laboratory (2025), https://doi.org/10.13139/ORNLNCCS/2524534


DATA & FILE OVERVIEW

1. File List: 
- 2024-05-01 M2 AMMTO Fatigue Blanks 05.hdf5, which contains:
	- build notes
	- machine information
	- ambient print conditions
	- feedstock information
	- partwise process parameters
	- post-build reference images
	- test results
		- log10(cycles to failure)
	- layerwise scan path information
		- line: x1, y1, x2, y2, time
		- point: x, y, photodiode intensity
	- layerwise sensor images
		- visible/0: post-melt visible light
		- visible/1: post-recoat visible light
		- nir/0: temporally integrated sum image in the near infrared
		- nir/1: temporally integrated max image in the near infrared
		- nir/2: temporally integrated argmax image in the near infrared
	- layerwise part template images
	- layerwise sample template images
	- layerwise thermal simulation results
		- melt pool depth
		- melt pool length
		- melt pool width
		- time since start of melting (relative to the start of melting of each part)
	- layerwise X-ray computed tomography (XCT) results
		- raw XCT data
		- segmented flaws
	- layerwise anomaly detection results
		- 0: Powder
		- 1: Printed
		- 2: Recoater Hopping
		- 3: Recoater Streaking
		- 4: Incomplete Spreading
		- 5: Powder Mounding
		- 6: Debris
		- 7: Spatter on Powder
		- 8: Swelling
		- 9: Super-Elevation
		- 10: Misprint
		- 11: Stripe Boundary
		- 12: Over Melting
		- 13: Under Melting
		- 14: Localized Bright Spot
		- 15: Localized Dark Spot
		- 16: Dropped NIR Data
		- 17: Pitting
	- log file information
	
- Fatigue Results Summary, which contains:
	- specimen number
	- gage diameter (mm)
	- test temperature (°C)
	- frequency (Hz)
	- stress ratio
	- stress parameters
	- total cycles
	- failure location
	- test hours
	
- ASTM E466.stl
	- .stl file of the machine fatigue coupon geometry
	
- ASTM E466 Drawing.pdf
	- defines specified geometry of the fatigue coupon
	
- Methods.docx
	- description of methods for data collection and processing

2. Additional related data collected that was not included in the current data package: N/A

3. Are there multiple versions of the dataset? No


METHODOLOGICAL INFORMATION

1. Description of methods used for collection/generation of data: 
See Methods.docx

2. Methods for processing the data: 
See Methods.docx

3. Instrument- or software-specific information needed to interpret the data: 
Any software or library able to load .hdf5 files (e.g., HDFView, h5py)

4. Standards and calibration information, if appropriate: N/A

5. Environmental/experimental conditions: N/A

6. Describe any quality-assurance procedures performed on the data: N/A

7. People involved with sample collection, processing, analysis and/or submission:
	- Zackary Snow, 
	- Luke Scime, 
	- Chase Joslin, 
	- William Halsey, 
	- Andres Marquez Rossy, 
	- Amir Ziabari, 
	- Vincent Paquit, 
	- Ryan Dehoff
