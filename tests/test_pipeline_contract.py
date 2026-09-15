import numpy as np
from pipeline.models import StarDetectionResult
from pipeline.submission import results_to_submission_dataframe, validate_submission_dataframe

def test_submission_schema_and_blank_characterisation():
    results=[StarDetectionResult('STAR_0001',0,.12),StarDetectionResult('STAR_0002',1,.91,12.345678,850.2,2.4)]
    df=results_to_submission_dataframe(results)
    assert list(df.columns)==['star_id','prediction','confidence','period','depth_ppm','duration_hours']
    assert df.loc[0,'period']==''
    assert df.loc[1,'period']==12.345678
    assert validate_submission_dataframe(df)

def test_candidate_physical_radius_relation():
    depth_ppm=1000.0
    rp_rs=np.sqrt(depth_ppm*1e-6)
    assert np.isclose(rp_rs,0.0316227766,rtol=1e-6)
