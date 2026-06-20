INSERT INTO turbines (code, name, farm_name, model, rated_power_kw, blade_count, status, latitude, longitude, created_by)
SELECT 'WT-001', '1号风机', '北海风电场', 'GW-2.0MW', 2000, 3, 'operating'::turbine_status, 39.9042, 116.4074, id FROM users WHERE username = 'inspector01'
UNION ALL
SELECT 'WT-002', '2号风机', '北海风电场', 'GW-2.5MW', 2500, 3, 'operating'::turbine_status, 39.9100, 116.4200, id FROM users WHERE username = 'inspector01'
UNION ALL
SELECT 'WT-003', '3号风机', '北海风电场', 'GW-3.0MW', 3000, 3, 'inspection'::turbine_status, 39.9200, 116.4300, id FROM users WHERE username = 'inspector01';

INSERT INTO route_plans (turbine_id, name, description, waypoint_count, altitude_m, created_by)
SELECT t.id, '标准三面巡检航线', '覆盖迎风面、背风面、前缘三面拍摄', 12, 35.0, u.id
FROM turbines t CROSS JOIN users u
WHERE u.username = 'inspector01' AND t.code = 'WT-001';

INSERT INTO route_plans (turbine_id, name, description, waypoint_count, altitude_m, created_by)
SELECT t.id, '近距详查航线', '针对前缘裂纹的近距离拍摄', 16, 25.0, u.id
FROM turbines t CROSS JOIN users u
WHERE u.username = 'inspector01' AND t.code = 'WT-001';

INSERT INTO grid_connections (turbine_id, status)
SELECT id, 'pending'::grid_status FROM turbines;
