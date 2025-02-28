require('dotenv').config();
const express = require('express');
const { CodeSandbox } = require('@codesandbox/sdk');

// Add timestamp to logs
const log = (message, type = 'info') => {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}`;
    switch(type) {
        case 'error':
            console.error(logMessage);
            break;
        case 'warn':
            console.warn(logMessage);
            break;
        default:
            console.log(logMessage);
    }
};

const app = express();
app.use(express.json());

// Enhanced environment validation
const requiredEnvVars = ['CSB_API_KEY'];
const missingVars = requiredEnvVars.filter(varName => !process.env[varName]);
if (missingVars.length > 0) {
    log(`Missing required environment variables: ${missingVars.join(', ')}`, 'error');
    process.exit(1);
}

log('Initializing CodeSandbox SDK...');
const sdk = new CodeSandbox(process.env.CSB_API_KEY);
log('CodeSandbox SDK initialized successfully');

// Add request logging middleware
app.use((req, res, next) => {
    log(`Incoming ${req.method} request to ${req.path}`);
    next();
});

// Status endpoint for health checks
app.get('/status', (req, res) => {
    res.json({
        status: 'ok',
        service: 'codesandbox-service',
        timestamp: new Date().toISOString()
    });
});

app.post('/execute', async (req, res) => {
    const requestId = Math.random().toString(36).substring(7);
    log(`[${requestId}] Starting code execution request`);

    const { code } = req.body;
    if (!code) {
        log(`[${requestId}] No code provided in request`, 'error');
        return res.status(400).json({ error: 'No code provided' });
    }

    log(`[${requestId}] Code to execute: ${code.substring(0, 100)}${code.length > 100 ? '...' : ''}`);

    const startTime = Date.now();
    const metrics = {
        workspaceCreation: 0, // Renamed from initialization to workspaceCreation for consistency with Python script
        codeExecution: 0,
        cleanup: 0
    };

    let sandbox = null;

    try {
        const createStart = Date.now();
        log(`[${requestId}] Creating sandbox instance`);
        sandbox = await sdk.sandbox.create();
        metrics.workspaceCreation = Date.now() - createStart; // Measure workspace creation time
        log(`[${requestId}] Sandbox created successfully in ${metrics.workspaceCreation}ms`);

        const execStart = Date.now();
        log(`[${requestId}] Executing code in sandbox`);
        const result = await sandbox.shells.python.run(code);
        metrics.codeExecution = Date.now() - execStart; // Measure code execution time
        log(`[${requestId}] Code execution completed in ${metrics.codeExecution}ms`);
        log(`[${requestId}] Execution output: ${JSON.stringify(result.output)}`);

        const cleanupStart = Date.now();
        log(`[${requestId}] Starting sandbox cleanup`);
        await sandbox.hibernate();
        metrics.cleanup = Date.now() - cleanupStart; // Measure cleanup time
        log(`[${requestId}] Cleanup completed in ${metrics.cleanup}ms`);

        const totalTime = Date.now() - startTime;
        log(`[${requestId}] Total request processing time: ${totalTime}ms`);

        res.json({
            requestId,
            output: result.output,
            metrics: metrics,
            totalTime
        });

    } catch (error) {
        log(`[${requestId}] Error during execution: ${error.message}`, 'error');
        log(`[${requestId}] Error stack: ${error.stack}`, 'error');

        // Attempt cleanup if sandbox exists
        if (sandbox) {
            try {
                log(`[${requestId}] Attempting cleanup after error`);
                const cleanupStart = Date.now();
                await sandbox.hibernate();
                metrics.cleanup = Date.now() - cleanupStart; // Measure cleanup time even in error case
                log(`[${requestId}] Cleanup after error successful in ${metrics.cleanup}ms`);
            } catch (cleanupError) {
                log(`[${requestId}] Cleanup after error failed: ${cleanupError.message}`, 'error');
            }
        }

        res.status(500).json({
            requestId,
            error: error.message,
            metrics: metrics,
            errorDetails: {
                name: error.name,
                message: error.message,
                stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
            }
        });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    log(`Unhandled error: ${err.message}`, 'error');
    log(err.stack, 'error');
    res.status(500).json({
        error: 'Internal server error',
        message: err.message,
        stack: process.env.NODE_ENV === 'development' ? err.stack : undefined
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    log(`CodeSandbox service running on port ${PORT}`);
    log(`Environment: ${process.env.NODE_ENV || 'development'}`);
    log('Server is ready to accept requests');
});

// Handle process termination
process.on('SIGTERM', () => {
    log('SIGTERM received. Shutting down gracefully');
    process.exit(0);
});

process.on('SIGINT', () => {
    log('SIGINT received. Shutting down gracefully');
    process.exit(0);
});

process.on('uncaughtException', (err) => {
    log(`Uncaught Exception: ${err.message}`, 'error');
    log(err.stack, 'error');
    process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
    log('Unhandled Rejection at:', 'error');
    log(`Promise: ${promise}`, 'error');
    log(`Reason: ${reason}`, 'error');
});