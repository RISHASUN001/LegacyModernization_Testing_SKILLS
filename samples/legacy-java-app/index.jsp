<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Legacy Application - Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
            padding: 20px;
        }
        
        .login-container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 400px;
            padding: 40px;
        }
        
        .login-header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .login-header h1 {
            margin: 0 0 5px 0;
            color: #333;
            font-size: 24px;
        }
        
        .login-header p {
            margin: 0;
            color: #999;
            font-size: 14px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: bold;
            font-size: 14px;
        }
        
        input[type="email"],
        input[type="password"],
        select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
            background: #f9f9f9;
        }
        
        input[type="email"]:focus,
        input[type="password"]:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
            background: white;
        }
        
        .error-message {
            background: #ffebee;
            color: #c62828;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 13px;
            display: none;
        }
        
        <% if (request.getAttribute("error") != null) { %>
            .error-message { display: block; }
        <% } %>
        
        .login-button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .login-button:hover {
            transform: translateY(-2px);
        }
        
        .login-button:active {
            transform: translateY(0);
        }
        
        .demo-credentials {
            background: #f0f4ff;
            border-left: 3px solid #667eea;
            padding: 15px;
            margin-top: 20px;
            font-size: 12px;
            color: #555;
            border-radius: 4px;
        }
        
        .demo-credentials strong {
            display: block;
            margin-bottom: 5px;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>Legacy App</h1>
            <p>Authentication System (Java/JSP)</p>
        </div>
        
        <% if (request.getAttribute("error") != null) { %>
            <div class="error-message">
                <%= request.getAttribute("error") %>
            </div>
        <% } %>
        
        <form method="POST" action="login" accept-charset="UTF-8">
            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" required value="admin">
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required value="password123">
            </div>
            
            <div class="form-group">
                <label for="module">Select Module</label>
                <select id="module" name="module" required>
                    <option value="Checklist">Checklist Module</option>
                    <option value="PaymentModule">Payment Module</option>
                    <option value="InventorySystem">Inventory System</option>
                    <option value="UserAuthentication">User Authentication</option>
                </select>
            </div>
            
            <button type="submit" class="login-button">Login to Dashboard</button>
        </form>
        
        <div class="demo-credentials">
            <strong>Demo Credentials:</strong>
            Email: admin<br>
            Password: password123
        </div>
    </div>
</body>
</html>
