package com.legacyapp.servlet;

import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;
import java.io.IOException;
import java.util.logging.Logger;

@WebServlet("/login")
public class LoginServlet extends HttpServlet {
    private static final Logger logger = Logger.getLogger(LoginServlet.class.getName());
    private static final String USERNAME = "admin";
    private static final String PASSWORD = "password123";

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        
        String email = request.getParameter("email");
        String password = request.getParameter("password");
        String module = request.getParameter("module");
        
        logger.info("Login attempt for user: " + email);
        
        // Simple authentication (legacy - no password hashing)
        if (isValidCredentials(email, password)) {
            HttpSession session = request.getSession();
            session.setAttribute("user", email);
            session.setAttribute("module", module);
            session.setMaxInactiveInterval(30 * 60); // 30 minutes
            
            logger.info("Login successful for user: " + email);
            response.sendRedirect("dashboard.jsp?module=" + module);
        } else {
            logger.warning("Login failed for user: " + email);
            request.setAttribute("error", "Invalid credentials");
            request.getRequestDispatcher("index.jsp").forward(request, response);
        }
    }

    private boolean isValidCredentials(String email, String password) {
        // Legacy authentication: hardcoded credentials
        return email != null && email.equals(USERNAME) && 
               password != null && password.equals(PASSWORD);
    }
}
