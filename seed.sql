insert into public.employees
    (employee_code, name, email, department, role, status, notes)
values
    ('EMP1001', 'Ananya Rao', 'ananya.rao@example.com', 'Application Support', 'Production Support Analyst', 'Active', 'Monitors payment services and incident queues.'),
    ('EMP1002', 'Arun Kumar', 'arun.kumar@example.com', 'Database Operations', 'Database Support Engineer', 'Active', 'Supports PostgreSQL health and query troubleshooting.'),
    ('EMP1003', 'Meera Joseph', 'meera.joseph@example.com', 'Service Management', 'Incident Coordinator', 'On Leave', 'Coordinates major incidents and stakeholder updates.'),
    ('EMP1004', 'Vijay Singh', 'vijay.singh@example.com', 'Platform Engineering', 'Linux Administrator', 'Active', 'Maintains Linux hosts and deployment automation.')
on conflict do nothing;
