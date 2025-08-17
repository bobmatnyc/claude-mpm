/**
 * Sample TypeScript file to test tree-sitter-typescript analysis
 * This file contains TypeScript-specific patterns and issues
 */

interface User {
    id: number;
    name: string;
    email: string;
    isActive: boolean;
}

interface Config {
    apiKey: string;
    timeout: number;
    retries: number;
}

// Security issue - hardcoded credentials
const config: Config = {
    apiKey: "prod-api-key-123456789",  // BAD: Hardcoded secret
    timeout: 30000,
    retries: 3
};

class TypeScriptUserService {
    private users: Map<number, User> = new Map();
    private connections: any[] = [];

    constructor(private config: Config) {}

    // Method with SQL injection vulnerability
    async findUserByEmail(email: string): Promise<User | null> {
        // BAD: String interpolation in SQL query
        const query = `SELECT * FROM users WHERE email = '${email}'`;
        return this.executeQuery(query);
    }

    // Complex method with high cyclomatic complexity
    processUserPermissions(user: User, permissions: string[]): any {
        let result: any = {};

        if (user.isActive) {
            if (permissions.includes('admin')) {
                if (user.email.endsWith('@company.com')) {
                    if (user.id > 1000) {
                        if (user.name.length > 5) {
                            if (permissions.includes('super_admin')) {
                                result.level = 'super_admin';
                                result.canDelete = true;
                                result.canModify = true;
                                result.canRead = true;
                            } else {
                                result.level = 'admin';
                                result.canDelete = false;
                                result.canModify = true;
                                result.canRead = true;
                            }
                        } else {
                            result.level = 'limited_admin';
                            result.canDelete = false;
                            result.canModify = false;
                            result.canRead = true;
                        }
                    } else {
                        result.level = 'junior_admin';
                        result.canDelete = false;
                        result.canModify = false;
                        result.canRead = true;
                    }
                } else {
                    result.level = 'external_admin';
                    result.canDelete = false;
                    result.canModify = false;
                    result.canRead = true;
                }
            } else if (permissions.includes('moderator')) {
                result.level = 'moderator';
                result.canDelete = false;
                result.canModify = true;
                result.canRead = true;
            } else {
                result.level = 'user';
                result.canDelete = false;
                result.canModify = false;
                result.canRead = true;
            }
        } else {
            result.level = 'inactive';
            result.canDelete = false;
            result.canModify = false;
            result.canRead = false;
        }

        return result;
    }

    // Performance issue - O(n²) complexity
    findDuplicateUsers(users: User[]): User[] {
        const duplicates: User[] = [];

        // BAD: Nested loops creating O(n²) complexity
        for (let i = 0; i < users.length; i++) {
            for (let j = i + 1; j < users.length; j++) {
                if (users[i].email === users[j].email) {
                    duplicates.push(users[i]);
                    duplicates.push(users[j]);
                }
            }
        }

        return duplicates;
    }

    // Unsafe any usage - type safety issue
    processAnyData(data: any): any {
        // BAD: Using 'any' defeats TypeScript's purpose
        return data.whatever.deeply.nested.property;
    }

    // Method with path traversal vulnerability
    readUserFile(filename: string): string {
        const fs = require('fs');
        // BAD: No path validation
        const fullPath = `/app/user-uploads/${filename}`;
        return fs.readFileSync(fullPath, 'utf8');
    }

    // Memory leak - missing cleanup
    setupEventHandlers(): void {
        const button = document.querySelector('#submit-btn');
        if (button) {
            button.addEventListener('click', this.handleSubmit.bind(this));
            // Missing: removeEventListener in cleanup
        }
    }

    private handleSubmit(): void {
        // Handler implementation
    }

    private async executeQuery(query: string): Promise<any> {
        // Simulate database query
        return {};
    }
}

// Generic type with overly complex constraints
interface ComplexGeneric<T extends Record<string, any> & {
    id: number;
    metadata: {
        tags: string[];
        properties: Record<string, unknown>;
    };
}> {
    data: T;
    validate(): boolean;
}

// Large function for testing function length detection
function massiveTypeScriptFunction(): string {
    const line1: string = "This is line 1";
    const line2: string = "This is line 2";
    const line3: string = "This is line 3";
    const line4: string = "This is line 4";
    const line5: string = "This is line 5";
    const line6: string = "This is line 6";
    const line7: string = "This is line 7";
    const line8: string = "This is line 8";
    const line9: string = "This is line 9";
    const line10: string = "This is line 10";
    const line11: string = "This is line 11";
    const line12: string = "This is line 12";
    const line13: string = "This is line 13";
    const line14: string = "This is line 14";
    const line15: string = "This is line 15";
    const line16: string = "This is line 16";
    const line17: string = "This is line 17";
    const line18: string = "This is line 18";
    const line19: string = "This is line 19";
    const line20: string = "This is line 20";
    const line21: string = "This is line 21";
    const line22: string = "This is line 22";
    const line23: string = "This is line 23";
    const line24: string = "This is line 24";
    const line25: string = "This is line 25";
    const line26: string = "This is line 26";
    const line27: string = "This is line 27";
    const line28: string = "This is line 28";
    const line29: string = "This is line 29";
    const line30: string = "This is line 30";
    const line31: string = "This is line 31";
    const line32: string = "This is line 32";
    const line33: string = "This is line 33";
    const line34: string = "This is line 34";
    const line35: string = "This is line 35";
    const line36: string = "This is line 36";
    const line37: string = "This is line 37";
    const line38: string = "This is line 38";
    const line39: string = "This is line 39";
    const line40: string = "This is line 40";
    const line41: string = "This is line 41";
    const line42: string = "This is line 42";
    const line43: string = "This is line 43";
    const line44: string = "This is line 44";
    const line45: string = "This is line 45";
    const line46: string = "This is line 46";
    const line47: string = "This is line 47";
    const line48: string = "This is line 48";
    const line49: string = "This is line 49";
    const line50: string = "This is line 50";
    const line51: string = "This is line 51";
    const line52: string = "This is line 52";
    const line53: string = "This is line 53";
    const line54: string = "This is line 54";
    const line55: string = "This is line 55";
    const line56: string = "This is line 56";
    const line57: string = "This is line 57";
    const line58: string = "This is line 58";
    const line59: string = "This is line 59";
    const line60: string = "This is line 60";
    const line61: string = "This is line 61";
    const line62: string = "This is line 62";
    const line63: string = "This is line 63";
    const line64: string = "This is line 64";
    const line65: string = "This is line 65";
    const line66: string = "This is line 66";
    const line67: string = "This is line 67";
    const line68: string = "This is line 68";
    const line69: string = "This is line 69";
    const line70: string = "This is line 70";
    const line71: string = "This is line 71";
    const line72: string = "This is line 72";
    const line73: string = "This is line 73";
    const line74: string = "This is line 74";
    const line75: string = "This is line 75";
    const line76: string = "This is line 76";
    const line77: string = "This is line 77";
    const line78: string = "This is line 78";
    const line79: string = "This is line 79";
    const line80: string = "This is line 80";
    const line81: string = "This is line 81";
    const line82: string = "This is line 82";
    const line83: string = "This is line 83";
    const line84: string = "This is line 84";
    const line85: string = "This is line 85";
    const line86: string = "This is line 86";
    const line87: string = "This is line 87";
    const line88: string = "This is line 88";
    const line89: string = "This is line 89";
    const line90: string = "This is line 90";
    const line91: string = "This is line 91";
    const line92: string = "This is line 92";
    const line93: string = "This is line 93";
    const line94: string = "This is line 94";
    const line95: string = "This is line 95";
    const line96: string = "This is line 96";
    const line97: string = "This is line 97";
    const line98: string = "This is line 98";
    const line99: string = "This is line 99";
    const line100: string = "This is line 100";
    const line101: string = "This is line 101";
    const line102: string = "This is line 102";
    const line103: string = "This is line 103";
    const line104: string = "This is line 104";
    const line105: string = "This is line 105";

    return `Processed ${line1} through ${line105}`;
}

// Async function with synchronous operations
async function processDataSynchronously(data: any[]): Promise<any[]> {
    const fs = require('fs');
    const results: any[] = [];

    for (const item of data) {
        // BAD: Synchronous I/O in async function
        const content = fs.readFileSync(`/tmp/${item.id}.json`, 'utf8');
        results.push(JSON.parse(content));
    }

    return results;
}

export {
    User,
    Config,
    TypeScriptUserService,
    ComplexGeneric,
    massiveTypeScriptFunction,
    processDataSynchronously
};
