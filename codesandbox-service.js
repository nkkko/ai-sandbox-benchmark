// codesandbox-service.js
require('dotenv').config();  // Add this line at the top
const express = require('express');
const { CodeSandbox } = require('@codesandbox/sdk');

const app = express();
app.use(express.json());

// Check if API key is available
if (!process.env.CSB_API_KEY) {
    console.error('Error: CSB_API_KEY environment variable is not set');
    process.exit(1);
}

const sdk = new CodeSandbox(process.env.CSB_API_KEY);

app.post('/execute', async (req, res) => {
    const { code } = req.body;
    const startTime = Date.now();
    const metrics = {
        initialization: 0,
        workspaceCreation: 0,
        codeExecution: 0,
        cleanup: 0
    };

    try {
        metrics.initialization = Date.now() - startTime;

        const createStart = Date.now();
        const sandbox = await sdk.sandbox.create();
        metrics.workspaceCreation = Date.now() - createStart;

        const execStart = Date.now();
        const result = await sandbox.shells.python.run(code);
        metrics.codeExecution = Date.now() - execStart;

        const cleanupStart = Date.now();
        await sandbox.hibernate();
        metrics.cleanup = Date.now() - cleanupStart;

        res.json({
            output: result.output,
            metrics: metrics
        });
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({
            error: error.message,
            metrics: metrics
        });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`CodeSandbox service running on port ${PORT}`);
});