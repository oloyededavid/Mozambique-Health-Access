---
title: "Travel time to health facilities in Mozambique: how district access estimates change with the facility list, mode of travel and facility functionality"
author: "David Oloyede"
date: "{{date}}"
---

# In brief

With motor transport, between {{AB_m60}}% and {{B_m60}}% of people in Mozambique are modelled to live more than an hour from a health facility, depending on which of two open facility lists, or both together, is used; on foot the figure is between {{AB_w60}}% and {{B_w60}}%. These national figures move by a few percentage points with the facility list, but the figure for a single district can move by up to {{ab_max_m}} points, and the choice of population map matters as much. All travel times here are modelled, not measured.

# Abstract

Estimates of how far people live from health care depend on which facilities are counted, how people are assumed to travel and where the population is placed. We modelled travel time to the nearest health facility across Mozambique's {{n_districts}} second-level units (geoBoundaries ADM2) with the Malaria Atlas Project 2020 friction surfaces and WorldPop 2020 population, and repeated the calculation with two facility lists: the public-sector list of Maina et al. (2019) (list A, {{a_used}} facilities) and the OpenStreetMap health facilities exported by the Humanitarian OpenStreetMap Team (list B, {{b_used}} facilities without pharmacies). With motorized transport, {{A_m60}}% of residents are modelled to live more than one hour from a list A facility and {{B_m60}}% from a list B facility; on foot the shares are {{A_w60}}% and {{B_w60}}%. Across districts, the share beyond one hour under the two lists has a rank correlation of {{ab_rho_m}} by motor and {{ab_rho_w}} on foot, and {{ab_10_m}} and {{ab_10_w}} districts change by more than 10 percentage points. Counting hospitals only, or switching from motorized to walking travel, tended to reorder districts more (intervals overlap). Replacing the WorldPop R2025A constrained population layer with the older unconstrained layer raises the national motorized share from {{A_m60}}% to {{A_m60u}}%, more than switching lists does; the two layers differ in release and inputs as well as in constraint. In three provinces in the north and centre, removing the {{h_non}} facilities (of {{h_non_file}} in the file) that the WHO HeRAMS survey reports as not functioning barely changes the provincial share on foot ({{H_all_h3_w60}}% to {{H_func_h3_w60}}%), but a few districts move by up to {{hf_max_w}} points. All travel times are modelled; none was compared with measured journeys.

**Keywords:** geographic access; health facilities; travel time; friction surface; OpenStreetMap; Mozambique

# 1. Introduction

Travel time to the nearest health facility is a common measure of geographic access. It is modelled by combining a map of facility locations with a friction surface, which gives the time needed to cross each grid cell, and with a gridded population map (Weiss et al., 2018; Weiss et al., 2020). Weiss et al. (2020) published global maps of travel time to health care for motorized and walking travel, built from facility locations compiled from OpenStreetMap, Google Maps and academic sources, including the public-sector list of Maina et al. (2019). An earlier geocoded inventory of public hospitals by the same group was used to estimate access to emergency hospital care across sub-Saharan Africa (Ouma et al., 2018), and earlier work in Mozambique modelled walking and driving access to health centres by province (dos Anjos Luis & Cabral, 2016).

Each input carries choices. Facility lists differ in coverage and in how facilities were located. Hierink et al. (2022) showed that the choice of gridded population dataset alone can change sub-national coverage by more than 70% at a one-hour threshold. Facilities that are listed may also not be working: humanitarian surveys such as the WHO Health Resources and Services Availability Monitoring System (HeRAMS) record whether each facility is functioning. Limited evidence was found in the reviewed literature of studies that vary these inputs together.

This study asks how much district estimates of travel time in Mozambique change with the facility list, the mode of travel, the type of facility counted, facility functionality and the population layer. It does not ask whether the modelled times are correct, which would need measured journeys.

# 2. Data and methods

## 2.1 Facility lists

**List A** is the Mozambique part of the public-sector health facility database of Maina et al. (2019), distributed as the file "00 SSA MFL (130219).xlsx" (Snow et al., 2019; figshare, CC0). It has {{a_rows}} facilities, all with coordinates: {{a_cs}} health centres (*centros de saúde*), {{a_ps}} health posts and {{a_hosp_all}} hospitals. Of these, {{a_used}} lie within 1 km of the national outline and are used. The database also lists facilities in the six neighbouring countries; {{cross_n}} of them fall inside the analysis grid and are used only in a sensitivity run.

**List B** is the OpenStreetMap health-facility layer for Mozambique exported by the Humanitarian OpenStreetMap Team (Humanitarian OpenStreetMap Team, 2026; file updated on the Humanitarian Data Exchange on {{osm_date}}, ODbL). Of its {{b_feat}} features, we count a feature as a health facility when its `amenity` tag is clinic, hospital, doctors or health post, or, when `amenity` is missing, its `healthcare` tag is clinic, hospital, centre, doctor or health post. This gives {{b_used}} facilities used, {{b_hosp}} of them hospitals. The {{b_pharm}} pharmacies are left out of the main run because they do not offer consultations, and are added back as a sensitivity run, in which the {{b_pharm_used}} that lie within Mozambique are used. Another {{b_excl}} features are left out: {{b_excl_list}}. Buildings and grounds mapped as outlines ({{b_poly}} features) are reduced to one point inside the outline. OpenStreetMap records no ownership for most features, so list B mixes public and private facilities.

Hospitals are the list A facility types that start with "Hospital" (rural, district, provincial, general and central hospitals), and the list B features tagged as hospitals. The two definitions are not the same, and list B counts {{b_hosp}} hospitals against {{a_hosp}} in list A.

## 2.2 Facility functionality

The WHO HeRAMS file for Mozambique, 2022 to 2024 by quarter (Humanitarian Data Exchange, CC BY), covers Cabo Delgado, Nampula and Zambézia only (WHO, 2024). It has {{h_rows}} assessment rows. Facility codes are repeated across different facilities, so we identify a facility by its cleaned name and its province and district, which gives {{h_fac}} facilities, and keep the latest assessment of each. The latest assessments range from {{h_q_first}} to {{h_q_last}}, and {{h_q_2024}} are from 2024, so the file is not a single snapshot. No assessment gives coordinates for {{h_nocoord}} facilities; one more had its coordinates one column to the right and was corrected. Of the {{h_points}} facilities with coordinates, we drop those more than 1 km outside Mozambique or outside the province they report, leaving {{h_used}}. Of these, {{h_approx}} are marked as having approximate coordinates and are kept. The functionality field (`HFFUNCT`) of the {{h_used}} used facilities reads fully functioning for {{h_full}}, partially functioning for {{h_part}}, non-functioning for {{h_non}} and is empty for {{h_miss}}. In the whole file, {{h_non_file}} facilities are reported non-functioning at their latest assessment; {{h_non}} of them have usable coordinates.

We compare three rules: every used facility (listed, with usable coordinates); every facility except those reported non-functioning (main rule); and only facilities reported fully functioning (strict rule, which also drops those with an empty field). Outside the three provinces, list A facilities are added unchanged, so that people near a provincial border can still reach facilities across it. Only the districts of the three provinces are reported for these runs.

## 2.3 Travel time

Travel time comes from the Malaria Atlas Project friction surfaces for 2020 (Weiss et al., 2020), one for motorized travel and one for walking only, at 30 arc-seconds (about 0.9 km). Each gives the minutes needed to cross one metre of a cell. We cut them to Mozambique plus about one degree, and computed the time from every cell to the nearest facility as the least-cost path over a graph that links each cell to its eight neighbours. The cost of a link is the mean friction of its two cells times the great-circle distance between their centres, so that cells narrower in longitude towards the south cost less to cross from east to west. The paths were found with Dijkstra's algorithm from all facilities at once (SciPy; Virtanen et al., 2020). A facility on a sea cell at the coast is moved to the nearest land cell within three cells ({{snap_a}} in list A and {{snap_b}} in list B).

The sea is impassable: it is taken as the cells where the Malaria Atlas Project's own published travel-time layer has no value. Inland water such as Lake Niassa and Cahora Bassa keeps the friction surface's values. Paths may cross neighbouring countries, but in the main runs only facilities in Mozambique are destinations. Residents who cannot reach any facility, mostly on islands without a listed facility, count as beyond every threshold; with lists A and B together and motorized travel they number about {{unreach_k}} thousand. A sensitivity run lets paths cross the sea at the friction surface's sea values, as a stand-in for boats and bridges.

## 2.4 Population and districts

Population is the WorldPop R2025A 2020 constrained layer at 100 m (Bondarenko et al., 2025), which places people only on cells mapped as settled; it totals {{pop_main}} million. The WorldPop 2000–2020 unconstrained layer for 2020, which spreads people over all land, totals {{pop_alt}} million and is used as a sensitivity run (WorldPop, 2018; Tatem, 2017). Each 100 m cell is assigned to the district that contains its centre and to the travel-time cell that contains its centre, so district totals are kept at 100 m while travel time is at about 0.9 km. People on sea cells at the coast are moved to the nearest land cell. Districts are the {{n_districts}} units of geoBoundaries gbOpen ADM2 for Mozambique (Runfola et al., 2020), grouped into the {{n_prov}} provinces of its ADM1 layer, in which Maputo city is part of Maputo province. Three units have fewer than {{min_pop}} residents ({{excluded}}) and are left out of the district comparisons, leaving {{n_compared}} districts.

## 2.5 Measures and comparisons

For each district, province and the whole country we report the population-weighted share of residents beyond one hour and beyond two hours, and the population-weighted median travel time. Two scenarios are compared through the district shares beyond one hour: the Spearman rank correlation across districts, with a 95% interval from 2,000 bootstrap resamples of districts; the median and largest change in percentage points; the number of districts that change by more than 10 points; and how many of the {{top_k}} districts with the highest share stay among the {{top_k}} highest. To see how much the results depend on a few facilities, we removed {{drop_share}}% of a list at random {{drop_runs}} times and recomputed the shares. To ask whether one choice reorders districts more than another, we resampled districts once for both comparisons and report the interval of the difference between the two rank correlations (paired bootstrap, 2,000 resamples).

# 3. Results

## 3.1 Positions of the facilities

In list A, {{a_out}} facilities lie more than 1 km outside Mozambique (at most {{a_out_max}} km), against {{b_out}} in list B (at most {{b_out_max}} km) and {{h_out}} in HeRAMS (at most {{h_out_max}} km). In the same order, {{a_sea}}, {{b_sea}} and {{h_sea}} facilities fall on a sea cell of the grid, usually because the 0.9 km cell at the coast is mostly sea, and {{a_water}}, {{b_water}} and {{h_water}} on a cell of inland water. The point lies in a different province from the one its source reports for {{a_mismatch}} of the list A facilities and {{h_mismatch}} of the HeRAMS facilities.

The two lists overlap closely where both have a facility. Of the list B facilities, {{ba_100}}% lie within 100 m of a list A facility, and the median distance from a list B facility to the nearest list A facility is {{ba_med}} m, which suggests that many OpenStreetMap points were copied from the same source or mapped from the same survey. In the other direction, {{ab_1k}}% of list A facilities have a list B facility within 1 km and {{ab_10k}}% have none within 10 km: list B is missing many rural facilities that list A has (Figure 1). In all, {{mutual}} pairs are each other's nearest neighbour within 1 km. HeRAMS facilities lie a median of {{ha_med}} m from the nearest list A facility, and {{ha_10k}}% are more than 10 km from any.

![**Figure 1.** Facilities used in the main runs. List A: Maina et al. (2019), public sector. List B: OpenStreetMap, without pharmacies. Open circles are hospitals.](paper/figures/fig1_facilities.png)

## 3.2 National and provincial estimates

With motorized transport, {{A_m60}}% of residents live more than one hour from a list A facility, {{B_m60}}% from a list B facility and {{AB_m60}}% from either (Table 1, Figure 2). On foot the shares are {{A_w60}}%, {{B_w60}}% and {{AB_w60}}%. Beyond two hours the motorized shares are {{A_m120}}%, {{B_m120}}% and {{AB_m120}}%, and the walking shares {{A_w120}}%, {{B_w120}}% and {{AB_w120}}%. The population-weighted median time is {{A_mmed}} minutes by motor and {{A_wmed}} minutes on foot with list A. The Malaria Atlas Project's published layers give {{published_m60}}% by motor and {{published_w60}}% on foot with the same population layer.

**Table 1.** Share of residents more than one hour from the nearest facility, by province (%). Population in millions, WorldPop R2025A constrained.

| Province | Population | Motorized, A | Motorized, B | Motorized, A and B | Walking, A | Walking, B | Walking, A and B |
|---|---|---|---|---|---|---|---|
{{prov_table}}

The largest provincial difference between the lists is in {{prov_gap_name}}, {{prov_gap_a}}% with list A against {{prov_gap_b}}% with list B by motor, a difference of {{prov_gap}} points. No province is much better covered by list B.

![**Figure 2.** Modelled travel time to the nearest facility of lists A and B together, 2020 friction surfaces, at about 0.9 km.](paper/figures/fig2_traveltime.png)

Counting hospitals only raises the national share beyond one hour to {{A_hosp_m60}}% (list A), {{B_hosp_m60}}% (list B) and {{AB_hosp_m60}}% (both) by motor, and to {{A_hosp_w60}}%, {{B_hosp_w60}}% and {{AB_hosp_w60}}% on foot (Figure 3). The population layer moves the national figures by more than the facility list. The two layers differ in release and inputs as well as in constraint, so the difference cannot be attributed to constraining alone. With the unconstrained layer the motorized share beyond one hour is {{A_m60u}}% for list A and {{AB_m60u}}% for both lists, against {{A_m60}}% and {{AB_m60}}% with the constrained layer; on foot it is {{A_w60u}}% and {{AB_w60u}}%. Switching from list A to list B adds {{dlist_m}} points by motor and {{dlist_w}} on foot, and switching the population layer adds {{dpop_m}} and {{dpop_w}} points. Adding facilities across the border ({{A_cross_m60}}% by motor), adding pharmacies to list B ({{B_pharm_m60}}%) or letting paths cross the sea ({{A_sea_m60}}% for list A) changes the national figure little.

![**Figure 3.** National share of residents more than one hour from the nearest facility under each scenario, with the constrained population layer (filled) and the unconstrained layer (open).](paper/figures/fig3_scenarios.png)

## 3.3 District estimates and rankings

District shares agree less than the national ones (Table 2, Figure 4). Between list A and list B, the rank correlation of the district shares beyond one hour is {{ab_rho_m}} by motor (95% interval {{ab_ci_m}}) and {{ab_rho_w}} on foot ({{ab_ci_w}}). By motor, {{ab_10_m}} districts change by more than 10 points, and {{ab_10_w}} on foot (Figure 5); {{ab_20_m}} and {{ab_20_w}} change by more than 20 points. The largest change is {{ab_max_m}} points by motor, in {{ab_max_m_d}}, and {{ab_max_w}} points on foot, in {{ab_max_w_d}}; list B has no facility in either district, where list A has {{ab_max_m_na}} and {{ab_max_w_na}}. Of the {{top_k}} districts with the highest motorized share under list A, {{ab_top_m}} are also among the {{top_k}} highest under list B ({{ab_top_w}} on foot). Adding list B to list A changes less: the rank correlation is {{aab_rho_m}} by motor and {{aab_rho_w}} on foot, and {{aab_10_m}} and {{aab_10_w}} districts change by more than 10 points.

**Table 2.** How district shares beyond one hour change between scenarios ({{n_compared}} districts unless stated). Each cell gives motorized / walking. Changes are in percentage points.

| Comparison | Rank correlation | Median change | Districts changing by more than 10 points | Largest change |
|---|---|---|---|---|
{{cmp_table}}

![**Figure 4.** District share of residents more than one hour from the nearest facility under list A and list B. Each point is a district; points above the line are districts where list B gives a longer time.](paper/figures/fig4_scatter.png)

![**Figure 5.** Change in each district's share of residents more than one hour from the nearest facility when list B replaces list A, in percentage points. Orange: more residents beyond one hour with list B; blue: fewer. Hatched units (a lake and two islands) are not compared.](paper/figures/fig5_change_map.png)

The mode of travel and the type of facility tended to reorder districts more than the facility list, although the intervals overlap (Figure 6). With both lists together, the rank correlation between motorized and walking shares is {{mode_rho}} ({{mode_ci}}), and only {{mode_top}} of the {{top_k}} districts with the highest motorized share are among the {{top_k}} highest on foot. Between all facilities and hospitals only, the rank correlation is {{hosp_rho_m}} by motor ({{hosp_ci_m}}) and {{hosp_rho_w}} on foot ({{hosp_ci_w}}). In the paired bootstrap, the rank correlation between lists A and B exceeds that between all facilities and hospitals by {{pd_hosp_m}} by motor (95% interval {{pd_hosp_m_ci}}) and {{pd_hosp_w}} on foot ({{pd_hosp_w_ci}}), and exceeds that between motorized and walking travel by {{pd_mode_m}} ({{pd_mode_m_ci}}) when the lists are compared by motor and {{pd_mode_w}} ({{pd_mode_w_ci}}) when they are compared on foot. Only the motorized intervals exclude zero. For hospitals alone, lists A and B give a rank correlation of {{hab_rho_m}} by motor, and {{hab_10_m}} districts change by more than 10 points, partly because the lists define hospitals differently.

![**Figure 6.** Rank correlation of district shares beyond one hour between pairs of runs, with 95% bootstrap intervals over districts. Lower values mean the choice reorders districts more. The intervals treat districts as independent, so they are likely too narrow.](paper/figures/fig6_rank.png)

The population layer changes district rankings about as much as the facility list: the rank correlation between the constrained and unconstrained layers is {{pop_rho_m}} by motor and {{pop_rho_w}} on foot, {{pop_10_m}} districts change by more than 10 points by motor, and the largest change is {{pop_max_m}} points in {{pop_max_d}}. The paired difference from the list comparison is {{pd_pop_m}} by motor ({{pd_pop_m_ci}}) and {{pd_pop_w}} on foot ({{pd_pop_w_ci}}). Facilities across the border change no district by more than {{cross_max_m}} points by motor and {{cross_max_w}} on foot (in {{cross_d_w}}). Pharmacies change {{pharm_10_w}} districts by more than 10 points on foot, the largest by {{pharm_max_w}} points ({{pharm_d_w}}). Opening the sea changes {{sea_d_m}} by {{sea_max_m}} points by motor and no district by more than {{sea_max_w}} on foot.

Removing {{drop_share}}% of list A at random {{drop_runs}} times leaves the national motorized share between {{drop_a_m_lo}}% and {{drop_a_m_hi}}% and the walking share between {{drop_a_w_lo}}% and {{drop_a_w_hi}}%. Single districts move more: in the median run the largest district change is {{drop_a_m_dmed}} points by motor (up to {{drop_a_m_dmax}}) and {{drop_a_w_dmed}} points on foot (up to {{drop_a_w_dmax}}). District estimates in sparsely served areas therefore rest on a few facilities each.

With list A, our travel times are close to the Malaria Atlas Project's published motorized layer: the rank correlation over the grid cells of Mozambique is {{pub_cell_a_m}} (every seventh cell), and the median difference is {{pub_med_a_m}} minutes (95th percentile {{pub_p95_a_m}} minutes). For walking it is {{pub_cell_a_w}}, and with list B {{pub_cell_b_m}} by motor. At district level the rank correlation with the published layer is {{pub_rho_a_m}} by motor and {{pub_rho_a_w}} on foot for list A, and {{pub_rho_b_m}} by motor for list B. This agreement is not an independent check. The published layer uses the same friction surface and its facility set includes the list of Maina et al. (2019); the agreement shows that our implementation reproduces theirs and that their facility set in Mozambique behaves like list A, not that either is correct.

## 3.4 Functioning facilities in Cabo Delgado, Nampula and Zambézia

Across the three provinces, the share of residents more than one hour from a HeRAMS facility on foot is {{H_all_h3_w60}}% when every listed facility with usable coordinates counts ({{h_used}} of {{h_fac}}), {{H_func_h3_w60}}% without the non-functioning ones and {{H_fully_h3_w60}}% when only fully functioning facilities count. By motor the shares are {{H_all_h3_m60}}%, {{H_func_h3_m60}}% and {{H_fully_h3_m60}}%. For comparison, list A gives {{A_h3_w60}}% on foot and {{A_h3_m60}}% by motor in the same provinces, and the rank correlation between list A and HeRAMS across the {{n_compared_h}} districts is {{ah_rho_m}} by motor and {{ah_rho_w}} on foot.

Removing the non-functioning facilities changes {{hf_10_w}} districts by more than 10 points on foot; the largest change is {{hf_max_w}} points in {{hf_d_w}} (by motor {{hf_max_m}} points, in {{hf_d_m}}). The strict rule changes more: {{hs_10_w}} districts change by more than 10 points on foot and {{hs_10_m}} by motor. The largest change in both modes is in {{hs_d}}: {{hs_max_w}} points on foot and {{hs_max_m}} by motor. The rank correlation with the all-facility run falls to {{hs_rho_w}} on foot ({{hs_ci_w}}) (Figure 7). The districts that change most under both rules are in {{hs_prov}}, but the strict rule also removes facilities whose status is simply missing.

![**Figure 7.** The twelve districts of Cabo Delgado, Nampula and Zambézia whose share of residents more than one hour from a facility on foot changes most between the HeRAMS rules.](paper/figures/fig7_herams.png)

# 4. Discussion

National estimates of geographic access in Mozambique are fairly stable across facility lists, but district estimates are not. A national motorized share of {{A_m60}}% to {{B_m60}}% beyond one hour hides districts whose share changes by {{ab_max_m}} points when one list replaces the other. The difference comes mainly from where list B is thin: its points largely coincide with list A where both have a facility, and many rural facilities in list A have no counterpart in OpenStreetMap. Combining the lists changes little relative to list A alone, so list A carries most of the coverage in these runs. That does not show list A is complete; it is a 2019 compilation and newer facilities may be missing from both lists.

The choice of population layer matters as much as the facility list at district level and more at national level, in line with the size of the differences reported by Hierink et al. (2022) for sub-Saharan Africa. The constrained layer places people on mapped settlements only and the unconstrained layer spreads people across all land. The two layers differ in release and inputs as well as in constraint, so the difference cannot be attributed to constraining alone. Neither is a census, and we cannot tell from these data which is closer to where people live.

Walking and motorized travel, and all facilities against hospitals, tended to rank districts differently enough that a list of "least served" districts depends on which question is asked. The HeRAMS comparison shows that facilities reported non-functioning change provincial figures little but matter for single districts. It covers three provinces and a mix of quarters from 2022 to 2024, so it cannot be extended to the rest of the country.

# 5. Limitations

All travel times are modelled from friction surfaces. They assume the fastest mode is always available, the nearest facility is always used, and travel is not affected by season, cost, security or queues, and they were not compared with measured travel times or survey reports. The friction surfaces date from 2020 and the population from 2020, while list A was compiled by 2019, OpenStreetMap was exported in 2026 and HeRAMS covers 2022 to 2024; the scenarios therefore mix dates. OpenStreetMap coverage depends on where mappers have worked and is uneven, and its hospital tag does not follow the national hierarchy. Facility coordinates in list A were not checked on the ground, and {{h_approx}} HeRAMS facilities report approximate coordinates. The 0.9 km grid cannot represent short bridges or causeways, and island residents depend on whether a facility is listed on the island. Facilities across the border are used only in a sensitivity run, and we do not know whether residents use them. District shares rest on modelled population and, in sparsely served districts, on a few facilities each, as the random-removal runs show. Bootstrap intervals treat districts as independent; neighbouring districts share facilities and roads, so the intervals are likely too narrow. The comparison with the Malaria Atlas Project's published layer uses the same friction surface and is not independent. This study measures geographic access only; it says nothing about quality of care, opening hours or whether services are affordable.

# 6. Conclusion

In Mozambique, the national share of residents modelled to live more than one hour from a health facility moves by a few points with the facility list and by more with the population layer, while district shares can move by tens of points. District rankings of access tended to change most with the mode of travel and the type of facility counted (intervals overlap, and a paired bootstrap separates them from the facility list only for motorized travel), less with the facility list and population layer, and least with facilities across the border, pharmacies or the treatment of the sea. Where district estimates guide planning, reporting them under more than one facility list and population layer, and saying which mode and facility type they assume, would show how much they can be relied on.

# Data and code availability

Code is released under the MIT licence and derived data under CC BY 4.0, from <https://github.com/oloyededavid/Mozambique-Health-Access>; files derived from OpenStreetMap remain under the ODbL. Source data keep their own terms: Maina et al. (2019) facility list (CC0), OpenStreetMap via the Humanitarian OpenStreetMap Team (ODbL), WHO HeRAMS via the Humanitarian Data Exchange (CC BY), Malaria Atlas Project friction surfaces (CC BY 4.0), WorldPop (CC BY 4.0) and geoBoundaries (CC BY 3.0 IGO for Mozambique).

# References

Bondarenko, M., Priyatikanto, R., Tejedor Garavito, N., Zhang, W., McKeen, T., et al. (2025). *Constrained estimates of 2015–2030 total number of people per grid square at a resolution of 3 arc (approximately 100m at the equator), R2025A version v1*. University of Southampton. https://doi.org/10.5258/SOTON/WP00839

dos Anjos Luis, A., & Cabral, P. (2016). Geographic accessibility to primary healthcare centers in Mozambique. *International Journal for Equity in Health*, 15, 173. https://doi.org/10.1186/s12939-016-0455-0

Hierink, F., Boo, G., Macharia, P. M., Ouma, P. O., et al. (2022). Differences between gridded population data impact measures of geographic access to healthcare in sub-Saharan Africa. *Communications Medicine*, 2, 117. https://doi.org/10.1038/s43856-022-00179-4

Humanitarian OpenStreetMap Team. (2026). *Health facilities of Mozambique* (OpenStreetMap export, file updated {{osm_date}}). Humanitarian Data Exchange. https://data.humdata.org/dataset/hotosm_moz_health_facilities

Maina, J., Ouma, P. O., Macharia, P. M., Alegana, V. A., et al. (2019). A spatial database of health facilities managed by the public health sector in sub Saharan Africa. *Scientific Data*, 6, 134. https://doi.org/10.1038/s41597-019-0142-2

Ouma, P. O., Maina, J., Thuranira, P. N., Macharia, P. M., et al. (2018). Access to emergency hospital care provided by the public sector in sub-Saharan Africa in 2015: a geocoded inventory and spatial analysis. *The Lancet Global Health*, 6(3), e342–e350. https://doi.org/10.1016/S2214-109X(17)30488-6

Runfola, D., Anderson, A., Baier, H., Crittenden, M., et al. (2020). geoBoundaries: A global database of political administrative boundaries. *PLOS ONE*, 15(4), e0231866. https://doi.org/10.1371/journal.pone.0231866

Snow, R. W., Maina, J., Ouma, P. O., Macharia, P. M., et al. (2019). *Public health facilities in sub Saharan Africa* [Data set]. figshare. https://doi.org/10.6084/m9.figshare.7725374.v1

Tatem, A. J. (2017). WorldPop, open data for spatial demography. *Scientific Data*, 4, 170004. https://doi.org/10.1038/sdata.2017.4

Virtanen, P., Gommers, R., Oliphant, T. E., et al. (2020). SciPy 1.0: fundamental algorithms for scientific computing in Python. *Nature Methods*, 17, 261–272. https://doi.org/10.1038/s41592-019-0686-2

Weiss, D. J., Nelson, A., Gibson, H. S., Temperley, W., et al. (2018). A global map of travel time to cities to assess inequalities in accessibility in 2015. *Nature*, 553, 333–336. https://doi.org/10.1038/nature25181

Weiss, D. J., Nelson, A., Vargas-Ruiz, C. A., Gligorić, K., et al. (2020). Global maps of travel time to healthcare facilities. *Nature Medicine*, 26, 1835–1838. https://doi.org/10.1038/s41591-020-1059-1

WHO. (2024). *Mozambique: Health facilities* (HeRAMS 2022–2024 by quarter). Humanitarian Data Exchange. https://data.humdata.org/dataset/health-cluster-mozambique

WorldPop. (2018). *Global 100m Population* (Mozambique, 2020, unconstrained). University of Southampton. https://doi.org/10.5258/SOTON/WP00645
