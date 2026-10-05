/* Analysis only. Link against the unmodified, pinned lwbgt source.
 * This wrapper exposes the SAME internal solar decomposition used by calc_wbgt.
 * It is never loaded by the application or installed over the production DLL.
 */
#include <math.h>
int calc_solar_parameters(int, int, double, float, float, float *, float *, float *);

int audit_solar(int year, int month, int day, int hour, int minute,
                int gmt, int averaging_minutes, double lat, double lon,
                double input_solar, double *values)
{
    double hour_gmt = hour - gmt + (minute - 0.5 * averaging_minutes) / 60.;
    float solar = (float)input_solar, cza, fdir;
    int status = calc_solar_parameters(year, month, day + hour_gmt / 24.,
                                      (float)lat, (float)lon, &solar, &cza, &fdir);
    if (status) return status;
    values[0] = solar;
    values[1] = cza;
    values[2] = fdir;
    values[3] = acos((double)cza) * 180. / 3.14159265358979323846;
    values[4] = (double)solar * fdir;
    values[5] = (double)solar * (1. - fdir);
    values[6] = cza > 0. ? (double)solar * fdir / cza : 0.;
    return 0;
}
