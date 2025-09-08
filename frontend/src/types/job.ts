export type JobStatus = "pending" | "active" | "processing" | "rendering" | "completed" | "failed" | "cancelled";

export interface Job {
    id: string;
    status: JobStatus;
    progress: number;
    currentStep: string;
    country?: string;
    platform?: string;
    genre?: string;
    contentType?: string;
    template?: string;
    workerId?: string;
    startedAt: string;
    completedAt?: string;
    duration?: string;
    videoUrl?: string;
    creatomateId?: string;
    error?: string;
    stepDetails?: {
        [stepNumber: number]: {
            creatomate_id?: string;
            error?: string;
            [key: string]: unknown;
        };
    };
    parameters?: {
        country: string;
        platform: string;
        genre: string;
        contentType: string;
        template: string;
        pauseAfterExtraction?: boolean;
    };
}
