-- ============================================================
-- 风电场叶片无人机巡检闭环系统 — 初始化迁移
-- PostgreSQL 16+
-- ============================================================

-- ---- 用户 ----
CREATE TYPE user_role AS ENUM ('inspector','annotator','supervisor');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    role user_role NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ---- 机组 ----
CREATE TYPE turbine_status AS ENUM ('operating','inspection','repair','offline');

CREATE TABLE turbines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    farm_name VARCHAR(128) NOT NULL,
    model VARCHAR(64),
    rated_power_kw INTEGER DEFAULT 2000,
    blade_count SMALLINT DEFAULT 3,
    status turbine_status DEFAULT 'operating',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ---- 航线计划 ----
CREATE TABLE route_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    turbine_id UUID NOT NULL REFERENCES turbines(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    waypoint_count INTEGER DEFAULT 8,
    altitude_m NUMERIC(6,1) DEFAULT 30,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ---- 巡检 ----
CREATE TYPE inspection_status AS ENUM ('draft','submitted');

CREATE TABLE inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    turbine_id UUID NOT NULL REFERENCES turbines(id),
    route_plan_id UUID REFERENCES route_plans(id),
    inspector_id UUID NOT NULL REFERENCES users(id),
    status inspection_status DEFAULT 'draft',
    inspection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    submitted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ---- 叶片照片 ----
CREATE TYPE blade_side AS ENUM ('pressure','suction','leading');

CREATE TABLE blade_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    blade_no SMALLINT NOT NULL CHECK (blade_no BETWEEN 1 AND 3),
    side blade_side NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    sha256 CHAR(64) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(64) DEFAULT 'image/jpeg',
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(inspection_id, blade_no, side)
);

-- ---- 缺陷 ----
CREATE TYPE defect_type AS ENUM ('crack','lightning','icing');
CREATE TYPE defect_severity AS ENUM ('L1','L2','L3','L4');
CREATE TYPE defect_status AS ENUM ('open','resolved');

CREATE TABLE defects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id UUID NOT NULL REFERENCES inspections(id),
    photo_id UUID NOT NULL REFERENCES blade_photos(id),
    blade_no SMALLINT NOT NULL,
    side blade_side NOT NULL,
    defect_type defect_type NOT NULL,
    severity defect_severity NOT NULL,
    previous_severity defect_severity,
    description TEXT,
    annotated_by UUID NOT NULL REFERENCES users(id),
    status defect_status DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ---- 维修单 ----
CREATE TYPE repair_decision AS ENUM ('repair','observe');
CREATE TYPE repair_status AS ENUM ('open','in_progress','closed');

CREATE TABLE repair_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    defect_id UUID NOT NULL REFERENCES defects(id),
    turbine_id UUID NOT NULL REFERENCES turbines(id),
    inspection_id UUID NOT NULL REFERENCES inspections(id),
    decision repair_decision NOT NULL,
    status repair_status DEFAULT 'open',
    supervisor_id UUID NOT NULL REFERENCES users(id),
    decided_at TIMESTAMPTZ DEFAULT now(),
    closed_at TIMESTAMPTZ,
    closure_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ---- 并网确认 ----
CREATE TYPE grid_status AS ENUM ('pending','frozen','confirmed');

CREATE TABLE grid_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    turbine_id UUID NOT NULL REFERENCES turbines(id),
    status grid_status DEFAULT 'pending',
    frozen_reason TEXT,
    frozen_by_defect_id UUID REFERENCES defects(id),
    confirmed_at TIMESTAMPTZ,
    confirmed_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ---- 追溯审计 ----
CREATE TYPE audit_entity AS ENUM ('inspection','defect','repair_order','photo','grid');
CREATE TYPE audit_action AS ENUM ('created','updated','submitted','annotated','escalated','closed','confirmed','frozen','unfrozen');

CREATE TABLE audit_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type audit_entity NOT NULL,
    entity_id UUID NOT NULL,
    action audit_action NOT NULL,
    operator_id UUID REFERENCES users(id),
    operator_role user_role,
    detail JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ---- 索引 ----
CREATE INDEX idx_photos_inspection ON blade_photos(inspection_id);
CREATE INDEX idx_defects_inspection ON defects(inspection_id);
CREATE INDEX idx_defects_turbine ON defects(inspection_id);
CREATE INDEX idx_repairs_defect ON repair_orders(defect_id);
CREATE INDEX idx_grid_turbine ON grid_connections(turbine_id);
CREATE INDEX idx_audit_entity ON audit_traces(entity_type, entity_id);

-- ---- 初始用户数据 ----
INSERT INTO users (username, display_name, role) VALUES
    ('inspector01', '张工（巡检工程师）', 'inspector'),
    ('annotator01', '李标注（AI标注员）', 'annotator'),
    ('supervisor01', '王主管（运维主管）', 'supervisor');

-- ---- 演示机组数据 ----
INSERT INTO turbines (code, name, farm_name, model, rated_power_kw, blade_count, status, latitude, longitude, created_by)
SELECT 'WT-001', '1号风机', '北海风电场', 'GW-2.0MW', 2000, 3, 'operating'::turbine_status, 39.9042, 116.4074, id FROM users WHERE username = 'inspector01'
UNION ALL
SELECT 'WT-002', '2号风机', '北海风电场', 'GW-2.5MW', 2500, 3, 'operating'::turbine_status, 39.9100, 116.4200, id FROM users WHERE username = 'inspector01'
UNION ALL
SELECT 'WT-003', '3号风机', '北海风电场', 'GW-3.0MW', 3000, 3, 'inspection'::turbine_status, 39.9200, 116.4300, id FROM users WHERE username = 'inspector01';

-- ---- 演示航线计划 ----
INSERT INTO route_plans (turbine_id, name, description, waypoint_count, altitude_m, created_by)
SELECT t.id, '标准三面巡检航线', '覆盖迎风面、背风面、前缘三面拍摄', 12, 35.0, u.id
FROM turbines t CROSS JOIN users u
WHERE u.username = 'inspector01' AND t.code = 'WT-001';

INSERT INTO route_plans (turbine_id, name, description, waypoint_count, altitude_m, created_by)
SELECT t.id, '近距详查航线', '针对前缘裂纹的近距离拍摄', 16, 25.0, u.id
FROM turbines t CROSS JOIN users u
WHERE u.username = 'inspector01' AND t.code = 'WT-001';

-- ---- 初始化并网确认记录 ----
INSERT INTO grid_connections (turbine_id, status)
SELECT id, 'pending'::grid_status FROM turbines;
