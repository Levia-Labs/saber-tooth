// Ids of running jobs whose progress toast the user closed or that timed out; one store for the page-started
// path (useJobRunner) and the list watcher (JobToasts), so a closed toast stays closed for the session.
export const dismissedJobs = new Set<string>();
