-- Grain: one randomized user. Left join preserves non-exposed users (ITT).
DROP VIEW IF EXISTS variant_summary;
DROP VIEW IF EXISTS retention_cohorts;
DROP VIEW IF EXISTS user_outcomes;
CREATE VIEW user_outcomes AS
SELECT a.user_id, a.variant, a.assigned_on, a.segment,
       CAST(julianday('{{as_of}}') - julianday(a.assigned_on) AS INTEGER) AS observed_days,
       MAX(CASE WHEN e.event_type='exposed' AND julianday(e.event_date)-julianday(a.assigned_on) BETWEEN 0 AND 6 THEN 1 ELSE 0 END) AS exposed,
       MAX(CASE WHEN e.event_type='workspace_created' AND julianday(e.event_date)-julianday(a.assigned_on) BETWEEN 0 AND 6 THEN 1 ELSE 0 END) AS workspace_created,
       MAX(CASE WHEN e.event_type='first_value' AND julianday(e.event_date)-julianday(a.assigned_on) BETWEEN 0 AND 6 THEN 1 ELSE 0 END) AS activated_7d,
       MAX(CASE WHEN e.event_type='support_contact' AND julianday(e.event_date)-julianday(a.assigned_on) BETWEEN 0 AND 6 THEN 1 ELSE 0 END) AS support_7d,
       MAX(CASE WHEN e.event_type='active' AND julianday(e.event_date)-julianday(a.assigned_on)=7 THEN 1 ELSE 0 END) AS retained_d7,
       MAX(CASE WHEN e.event_type='active' AND julianday(e.event_date)-julianday(a.assigned_on)=30 THEN 1 ELSE 0 END) AS retained_d30
FROM assignments a LEFT JOIN events e ON e.user_id=a.user_id
GROUP BY a.user_id,a.variant,a.assigned_on,a.segment;

CREATE VIEW variant_summary AS
SELECT variant, COUNT(*) AS assigned_users, SUM(exposed) AS exposed,
       SUM(workspace_created) AS workspace_created, SUM(activated_7d) AS activated_7d,
       SUM(support_7d) AS support_7d,
       SUM(CASE WHEN observed_days>=7 THEN 1 ELSE 0 END) AS primary_mature_users,
       SUM(CASE WHEN observed_days>=7 THEN retained_d7 ELSE 0 END) AS retained_d7,
       SUM(CASE WHEN observed_days>=7 THEN 1 ELSE 0 END) AS eligible_d7,
       SUM(CASE WHEN observed_days>=30 THEN retained_d30 ELSE 0 END) AS retained_d30,
       SUM(CASE WHEN observed_days>=30 THEN 1 ELSE 0 END) AS eligible_d30
FROM user_outcomes GROUP BY variant;

-- A cohort can be partially mature. Rates refer only to the displayed eligible users.
CREATE VIEW retention_cohorts AS
SELECT strftime('%Y-W%W',assigned_on) AS cohort_week, variant, COUNT(*) AS users,
       SUM(CASE WHEN observed_days>=7 THEN 1 ELSE 0 END) AS eligible_d7,
       SUM(CASE WHEN observed_days>=7 THEN retained_d7 ELSE 0 END) AS retained_d7,
       1.0*SUM(CASE WHEN observed_days>=7 THEN retained_d7 ELSE 0 END)/NULLIF(SUM(CASE WHEN observed_days>=7 THEN 1 ELSE 0 END),0) AS d7_rate,
       SUM(CASE WHEN observed_days>=30 THEN 1 ELSE 0 END) AS eligible_d30,
       SUM(CASE WHEN observed_days>=30 THEN retained_d30 ELSE 0 END) AS retained_d30,
       1.0*SUM(CASE WHEN observed_days>=30 THEN retained_d30 ELSE 0 END)/NULLIF(SUM(CASE WHEN observed_days>=30 THEN 1 ELSE 0 END),0) AS d30_rate
FROM user_outcomes GROUP BY strftime('%Y-W%W',assigned_on),variant;
