const Store = require('electron-store');
const { v4: uuidv4 } = require('uuid');

class Database {
    constructor() {
        this.store = new Store({
            name: 'learning-app-data',
            defaults: {
                users: [],
                materials: [],
                questions: [],
                errorRecords: [],
                currentUser: null
            }
        });
    }

    // 用户相关
    createUser(userData) {
        const users = this.store.get('users');
        const user = {
            id: uuidv4(),
            ...userData,
            createdAt: new Date().toISOString()
        };
        users.push(user);
        this.store.set('users', users);
        return user;
    }

    getUserByUsername(username) {
        const users = this.store.get('users');
        return users.find(user => user.username === username);
    }

    // 学习资料相关
    addMaterial(materialData) {
        const materials = this.store.get('materials');
        const material = {
            id: uuidv4(),
            ...materialData,
            createdAt: new Date().toISOString()
        };
        materials.push(material);
        this.store.set('materials', materials);
        return material;
    }

    getMaterials() {
        return this.store.get('materials');
    }

    // 错题本相关
    addErrorRecord(record) {
        const records = this.store.get('errorRecords');
        const errorRecord = {
            id: uuidv4(),
            ...record,
            createdAt: new Date().toISOString()
        };
        records.push(errorRecord);
        this.store.set('errorRecords', records);
        return errorRecord;
    }

    getErrorRecords() {
        return this.store.get('errorRecords');
    }
}

module.exports = new Database();