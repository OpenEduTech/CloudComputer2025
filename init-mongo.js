// 初始化副本集
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "mongo1:27017" },
    { _id: 1, host: "mongo2:27017" },
    { _id: 2, host: "mongo3:27017" }
  ]
});

// 等待副本集状态变为PRIMARY
while (rs.status().myState != 1) {
  sleep(1000);
}

// 创建用户和数据库
use admin;
db.createUser({
  user: "root",
  pwd: "example",
  roles: ["root"]
});

use study_agent_db;
db.createUser({
  user: "appuser",
  pwd: "apppassword",
  roles: [
    { role: "readWrite", db: "study_agent_db" },
    { role: "dbAdmin", db: "study_agent_db" }
  ]
});

print("MongoDB副本集初始化完成！");
