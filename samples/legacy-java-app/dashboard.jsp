<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%
    String user = (String) session.getAttribute("user");
    String module = (String) session.getAttribute("module");
    
    // Simple session check (legacy - no security framework)
    if (user == null) {
        response.sendRedirect("index.jsp");
        return;
    }
%>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Legacy Dashboard - <%= module %></title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        
        .header p {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .container {
            display: flex;
            min-height: calc(100vh - 80px);
        }
        
        .sidebar {
            width: 250px;
            background: white;
            padding: 20px;
            border-right: 1px solid #ddd;
            box-shadow: 2px 0 5px rgba(0, 0, 0, 0.05);
        }
        
        .sidebar-section {
            margin-bottom: 20px;
        }
        
        .sidebar-section-title {
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .sidebar-link {
            display: block;
            padding: 8px 12px;
            color: #666;
            text-decoration: none;
            border-radius: 4px;
            margin-bottom: 5px;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        
        .sidebar-link:hover {
            background-color: #f0f0f0;
            color: #333;
        }
        
        .content {
            flex: 1;
            padding: 30px;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .card-title {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .stat-item {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 12px;
            opacity: 0.9;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        table thead {
            background: #f5f5f5;
        }
        
        table th,
        table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        table tbody tr:hover {
            background: #f9f9f9;
        }
        
        .footer {
            background: white;
            border-top: 1px solid #ddd;
            padding: 20px;
            text-align: center;
            color: #999;
            font-size: 12px;
        }
        
        .logout-link {
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
            margin-left: 20px;
        }
        
        .logout-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1><%= module %> - Dashboard</h1>
        <p>Welcome, <%= user %>! | <a href="logout" class="logout-link">Logout</a></p>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="sidebar-section">
                <div class="sidebar-section-title">Navigation</div>
                <a href="#" class="sidebar-link">Dashboard</a>
                <a href="#" class="sidebar-link">Users</a>
                <a href="#" class="sidebar-link">Settings</a>
                <a href="#" class="sidebar-link">Reports</a>
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-section-title">Admin</div>
                <a href="#" class="sidebar-link">System Config</a>
                <a href="#" class="sidebar-link">Audit Log</a>
                <a href="#" class="sidebar-link">Database</a>
            </div>
        </div>
        
        <div class="content">
            <div class="card">
                <div class="card-title">Module: <%= module %></div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">1,234</div>
                        <div class="stat-label">Total Records</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">95%</div>
                        <div class="stat-label">Uptime</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">42</div>
                        <div class="stat-label">Active Users</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">12ms</div>
                        <div class="stat-label">Avg Response</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">Recent Activity</div>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Action</th>
                            <th>User</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>2024-04-13 14:22:45</td>
                            <td>User Created</td>
                            <td>admin</td>
                            <td>✓ Success</td>
                        </tr>
                        <tr>
                            <td>2024-04-13 14:15:30</td>
                            <td>Data Updated</td>
                            <td>user1</td>
                            <td>✓ Success</td>
                        </tr>
                        <tr>
                            <td>2024-04-13 14:10:12</td>
                            <td>Report Generated</td>
                            <td>admin</td>
                            <td>✓ Success</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <div class="footer">
        Legacy Application System | Last Sync: <%= System.currentTimeMillis() %> | v1.0
    </div>
</body>
</html>
