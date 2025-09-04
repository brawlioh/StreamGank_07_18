export interface QueueStats {
    pending: number;
    processing: number;
    rendering: number;
    completed: number;
    failed: number;
    activeWorkers: number;
    availableWorkers: number;
    concurrentProcessing: boolean;
    _debug?: string;
}
