/**
 * Professional File-based Logging System for Node.js
 * Provides structured, persistent logging for all job processes with rotation and search
 */

const fs = require('fs').promises;
const path = require('path');
const { createWriteStream } = require('fs');

class FileLogger {
    constructor(baseLogDir = 'docker_volumes/logs') {
        this.baseLogDir = path.resolve(baseLogDir);
        this.jobLogsDir = path.join(this.baseLogDir, 'jobs');
        this.systemLogsDir = path.join(this.baseLogDir, 'system');
        this.archivedLogsDir = path.join(this.baseLogDir, 'archived');

        // Create directories
        this.initDirectories();

        // Active log streams cache
        this.logStreams = new Map();

        // Log rotation settings
        this.maxFileSize = 10 * 1024 * 1024; // 10MB
        this.maxBackups = 5;

        console.log(`📝 FileLogger initialized: ${this.baseLogDir}`);
    }

    async initDirectories() {
        try {
            await fs.mkdir(this.baseLogDir, { recursive: true });
            await fs.mkdir(this.jobLogsDir, { recursive: true });
            await fs.mkdir(this.systemLogsDir, { recursive: true });
            await fs.mkdir(this.archivedLogsDir, { recursive: true });
        } catch (error) {
            console.error('❌ Failed to create log directories:', error);
        }
    }

    /**
     * Get or create a log stream for a specific job
     */
    getJobLogStream(jobId) {
        if (!this.logStreams.has(jobId)) {
            const logFile = path.join(this.jobLogsDir, `${jobId}.log`);
            const stream = createWriteStream(logFile, { flags: 'a', encoding: 'utf8' });

            stream.on('error', (error) => {
                console.error(`❌ Log stream error for job ${jobId}:`, error);
            });

            this.logStreams.set(jobId, stream);

            // Log job start
            this.logJobEvent(jobId, 'job_started', 'Job logging initialized (Node.js)', {
                log_file: logFile,
                timestamp: new Date().toISOString()
            });
        }

        return this.logStreams.get(jobId);
    }

    /**
     * Log a structured job event to file
     */
    logJobEvent(jobId, eventType, message, details = {}, level = 'info') {
        const logEntry = {
            timestamp: new Date().toISOString(),
            job_id: jobId,
            event_type: eventType,
            level: level,
            message: message,
            details: details,
            source: 'nodejs',
            process_time: Date.now()
        };

        const logLine = JSON.stringify(logEntry) + '\n';

        try {
            const stream = this.getJobLogStream(jobId);
            stream.write(logLine);

            // Also log to console for monitoring
            const shortJobId = jobId.slice(-8);
            console.log(`📝 [${shortJobId}] ${level.toUpperCase()}: ${message}`);
        } catch (error) {
            console.error(`❌ Failed to write log for job ${jobId}:`, error);
        }
    }

    /**
     * Log job queue events
     */
    logJobQueued(jobId, parameters) {
        this.logJobEvent(jobId, 'job_queued', 'Job added to processing queue', {
            parameters: parameters,
            queue_time: new Date().toISOString()
        });
    }

    logJobStarted(jobId, workerId) {
        this.logJobEvent(jobId, 'job_started', 'Job processing started', {
            worker_id: workerId,
            start_time: new Date().toISOString()
        });
    }

    logJobProgress(jobId, progress, currentStep, details = {}) {
        this.logJobEvent(jobId, 'job_progress', `Progress: ${progress}% - ${currentStep}`, {
            progress: progress,
            current_step: currentStep,
            ...details
        });
    }

    logJobCompleted(jobId, duration, result = {}) {
        this.logJobEvent(jobId, 'job_completed', `Job completed successfully in ${duration}s`, {
            duration: duration,
            completion_time: new Date().toISOString(),
            ...result
        });
    }

    logJobFailed(jobId, error, duration = null) {
        this.logJobEvent(
            jobId,
            'job_failed',
            `Job failed: ${error}`,
            {
                error: error,
                duration: duration,
                failure_time: new Date().toISOString()
            },
            'error'
        );
    }

    logWebhookReceived(jobId, stepNumber, stepName, status, details = {}) {
        this.logJobEvent(jobId, 'webhook_received', `Step ${stepNumber} ${status}: ${stepName}`, {
            step_number: stepNumber,
            step_name: stepName,
            step_status: status,
            webhook_time: new Date().toISOString(),
            ...details
        });
    }

    logCreatomateMonitoring(jobId, creatomateId, status, attempts = null) {
        this.logJobEvent(jobId, 'creatomate_monitoring', `Creatomate ${creatomateId}: ${status}`, {
            creatomate_id: creatomateId,
            render_status: status,
            monitoring_attempts: attempts,
            check_time: new Date().toISOString()
        });
    }

    /**
     * Read logs for a specific job
     */
    async readJobLogs(jobId, limit = 1000) {
        const logFile = path.join(this.jobLogsDir, `${jobId}.log`);

        try {
            const content = await fs.readFile(logFile, 'utf8');
            const lines = content
                .trim()
                .split('\n')
                .filter((line) => line);

            const logs = [];
            for (const line of lines) {
                try {
                    const logEntry = JSON.parse(line);
                    logs.push(logEntry);
                } catch (parseError) {
                    // Handle non-JSON lines
                    logs.push({
                        timestamp: new Date().toISOString(),
                        job_id: jobId,
                        event_type: 'raw_log',
                        level: 'info',
                        message: line,
                        details: {},
                        source: 'nodejs'
                    });
                }
            }

            // Return most recent logs first
            return logs.slice(-limit).reverse();
        } catch (error) {
            if (error.code === 'ENOENT') {
                return []; // File doesn't exist yet
            }
            throw error;
        }
    }

    /**
     * Search logs with filters
     */
    async searchLogs(filters = {}) {
        const { jobId, eventType, level, messageContains, limit = 100 } = filters;

        if (jobId) {
            // Search specific job
            const logs = await this.readJobLogs(jobId, 10000);
            return this.filterLogs(logs, filters).slice(0, limit);
        } else {
            // Search all jobs (expensive operation)
            const logFiles = await fs.readdir(this.jobLogsDir);
            const allLogs = [];

            for (const file of logFiles) {
                if (file.endsWith('.log')) {
                    const jobId = path.basename(file, '.log');
                    const logs = await this.readJobLogs(jobId, 1000);
                    allLogs.push(...logs);
                }
            }

            return this.filterLogs(allLogs, filters)
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                .slice(0, limit);
        }
    }

    filterLogs(logs, filters) {
        const { eventType, level, messageContains } = filters;

        return logs.filter((log) => {
            if (eventType && log.event_type !== eventType) return false;
            if (level && log.level !== level) return false;
            if (messageContains && !log.message.toLowerCase().includes(messageContains.toLowerCase())) return false;
            return true;
        });
    }

    /**
     * Archive completed job logs
     */
    async archiveJobLogs(jobId) {
        try {
            const sourceFile = path.join(this.jobLogsDir, `${jobId}.log`);
            const archiveFile = path.join(this.archivedLogsDir, `${jobId}_${Date.now()}.log`);

            // Move file to archive
            await fs.rename(sourceFile, archiveFile);

            // Close and remove stream
            const stream = this.logStreams.get(jobId);
            if (stream) {
                stream.end();
                this.logStreams.delete(jobId);
            }

            console.log(`📦 Archived logs for job ${jobId}`);
            return true;
        } catch (error) {
            console.error(`❌ Failed to archive logs for job ${jobId}:`, error);
            return false;
        }
    }

    /**
     * Get logging statistics
     */
    async getLogStats() {
        try {
            const jobFiles = await fs.readdir(this.jobLogsDir);
            const archivedFiles = await fs.readdir(this.archivedLogsDir);

            let totalSize = 0;
            for (const file of jobFiles) {
                if (file.endsWith('.log')) {
                    const filePath = path.join(this.jobLogsDir, file);
                    const stats = await fs.stat(filePath);
                    totalSize += stats.size;
                }
            }

            return {
                active_log_files: jobFiles.filter((f) => f.endsWith('.log')).length,
                archived_log_files: archivedFiles.filter((f) => f.endsWith('.log')).length,
                total_size_mb: (totalSize / (1024 * 1024)).toFixed(2),
                base_log_dir: this.baseLogDir,
                log_directories: {
                    jobs: this.jobLogsDir,
                    system: this.systemLogsDir,
                    archived: this.archivedLogsDir
                }
            };
        } catch (error) {
            console.error('❌ Failed to get log stats:', error);
            return {};
        }
    }

    /**
     * Clean up old archived logs
     */
    async cleanupOldLogs(daysOld = 30) {
        try {
            const cutoffTime = Date.now() - daysOld * 24 * 60 * 60 * 1000;
            const archivedFiles = await fs.readdir(this.archivedLogsDir);

            let deletedCount = 0;
            for (const file of archivedFiles) {
                if (file.endsWith('.log')) {
                    const filePath = path.join(this.archivedLogsDir, file);
                    const stats = await fs.stat(filePath);

                    if (stats.mtime.getTime() < cutoffTime) {
                        await fs.unlink(filePath);
                        deletedCount++;
                    }
                }
            }

            if (deletedCount > 0) {
                console.log(`🧹 Cleaned up ${deletedCount} old log files`);
            }

            return deletedCount;
        } catch (error) {
            console.error('❌ Failed to cleanup old logs:', error);
            return 0;
        }
    }

    /**
     * Close all log streams (for graceful shutdown)
     */
    closeAllStreams() {
        for (const [jobId, stream] of this.logStreams) {
            try {
                stream.end();
                console.log(`📝 Closed log stream for job ${jobId}`);
            } catch (error) {
                console.error(`❌ Error closing log stream for job ${jobId}:`, error);
            }
        }
        this.logStreams.clear();
    }
}

// Global file logger instance
let _fileLogger = null;

function getFileLogger() {
    if (!_fileLogger) {
        _fileLogger = new FileLogger();
    }
    return _fileLogger;
}

module.exports = {
    FileLogger,
    getFileLogger
};
