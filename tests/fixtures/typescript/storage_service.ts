// Backend-style TS service with interfaces, classes, generics, visibility
// modifiers, async methods, and module-level const exports.
import type { SomeType } from "./types";

const DB_NAME = "demo-db";
const DB_VERSION = 1;

interface DBSchema {
    projects: Project;
    documents: Document;
    settings: AppSettings;
}

export class StorageService {
    private db: IDBDatabase | null = null;
    private initPromise: Promise<void> | null = null;

    async init(): Promise<void> {
        if (this.initPromise) return this.initPromise;
        this.initPromise = this.doInit();
        return this.initPromise;
    }

    private async doInit(): Promise<void> {
        this.db = null;
    }

    // Generic CRUD
    private async getAll<T>(storeName: keyof DBSchema): Promise<T[]> {
        return [] as T[];
    }

    async getProject(id: string): Promise<Project | null> {
        return null;
    }

    async saveProject(project: Project): Promise<void> {
        // ...
    }

    protected log(msg: string): void {
        console.log(msg);
    }
}

export class LanguageService {
    private cache = new Map<string, string>();

    async getInstructions(lang: string): Promise<string> {
        return this.cache.get(lang) ?? "";
    }

    clearCache(): void {
        this.cache.clear();
    }
}

export const storage = new StorageService();
export const language = new LanguageService();
