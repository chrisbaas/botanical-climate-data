"""Basic non-botanical monthly climate descriptors; not C3d sufficient statistics."""
DAYS=(31,28.25,31,30,31,30,31,31,30,31,30,31)
def summarise(profile):
    av=profile['tavg']; p=profile['prec']
    return {
      'annual_mean_temperature_c':round(sum(x*d for x,d in zip(av,DAYS))/sum(DAYS),2),
      'coldest_monthly_mean_c':round(min(av),2),
      'warmest_monthly_mean_c':round(max(av),2),
      'annual_precipitation_mm':round(sum(p),1),
      'warm_month_count_mean_ge_10c':sum(x>=10 for x in av),
      'driest_month_precipitation_mm':round(min(p),1),
      'wettest_month_precipitation_mm':round(max(p),1),
      'winter_absolute_minimum_c':None,
      'frost_days_per_year':None,
      'reference_et0_mm':None,
    }
