-- ============================================================
-- 修复 grid_connections 唯一性约束
-- 确保同一机组只能有一条待处理（pending/frozen）并网记录
-- ============================================================

-- 首先清理可能存在的重复数据（只保留每个机组最新的非 confirmed 记录）
WITH duplicates AS (
    SELECT id, turbine_id, created_at,
           ROW_NUMBER() OVER (PARTITION BY turbine_id ORDER BY created_at DESC) as rn
    FROM grid_connections
    WHERE status != 'confirmed'
)
DELETE FROM grid_connections
WHERE id IN (
    SELECT id FROM duplicates WHERE rn > 1
);

-- 添加部分唯一索引：同一机组只能有一条非 confirmed 状态的记录
CREATE UNIQUE INDEX uq_grid_turbine_active 
ON grid_connections (turbine_id) 
WHERE status != 'confirmed';
