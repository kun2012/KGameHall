# KGameHall

A game hall server supports talking and playing games

# Usage

### Server

```
python GameHallServer.py [-h] [-o HOST] [-p PORT] [-n DBNAME] [-u CONNECTNUM]
                         [-d TIME_DELTA] [-l TIME_DURATION]

optional arguments:
  -h, --help	show this help message and exit
  -o, --host	Host name
  -p, --port	Server port
  -n, --dbname	Player database name
  -u, --connectnum	Number of client connection
  -d, --time_delta	21 point game time delta(in minutes)
  -l, --time_duration	21 point game time duration(in seconds)
```


### Client

```
python PlayerClient.py [hostname]
```


# 用户命令

$register username password		-- 注册新用户

$login username password		-- 用户登录

$chat message		-- 用户与当前位置（大厅或房间）的其他人聊天

$chat@username message		-- 用户与指定人聊天

$chatall message		-- 用户给所有人广播信息

$online_time		-- 查询当前在线时间

$history_online_time		-- 查询历史在线时间

$build roomname		-- 创建房间

$join roomname		-- 进入房间

$rooms		-- 查看当前存在的房间，并显示该房间的人数

$leave		-- 离开房间，返回大厅

$logout		-- 退出登录

$quit		-- 退出大厅

$21game math_expression		-- 参与21点游戏，提交符合要求的数学表达式


# 实现功能

1. 客户端可以账户名、密码登陆进入游戏大厅

2. 可以注册新用户

3. 支持聊天，例如输入$chat haha，则大厅里其他人可以看到haha

4. 账户有在线时长的属性，需要存盘，下线再上不会丢失数据

5. 进阶功能：
		
		i. 有创建房间，进入房间，退出房间功能
		
		ii. 支持多频道聊天，例如大厅，房间，私聊
		
		iii. 小游戏：21点
				
				a. 每个房间，每逢半点（8点半，9点，9点半等），会随机生成4个1到10内的数，发布在房间内，所有人可以看到;
				
				b. 玩家可以用+,-,*,/和括号，让4个数的计算结果尽量接近于21，但不能超过21;

				c. 玩家可以用聊天的方式，向服务端提供回答，例如: $21game (1+2)*(3+5)。只接受任意一个玩家第一次的回答，且此回答其他人看不到;

				d. 服务端发布问题后，15秒之内，如果有玩家的回答，刚好等于21，那么此玩家获胜，否则，计时结束时，计算结果最大的玩家获胜;



# 游戏聊天室实现的基本思想

1. 由于目前功能比较简单，server仅使用一个进程完成所有功能

2. 使用python的异步socket机制，自己管理socket的创建，通讯和销毁，核心语句为：

	```
	read_socks, write_socks, error_socks = select.select(self.all_socks, [], self.all_socks, 0.5)
	```

	Server对每个client的信息会使用socket.sendall(msg)返回消息，聊天的消息一般较短，不会产生太大的延时，因此并没有实现buffer，对可写的socket进行监听

	设置time_out为0.5秒是为了防止阻塞，实现定时21点游戏

3. 用户的信息（用户名，密码，登录时长）使用数据库sqlite3进行存储，并对密码进行AES加密

4. 用户可以在不同的频道（大厅，房间，私聊）进行聊天

5. 游戏会在每个房间定时开放，到一定时间后会宣布游戏结束并选出获胜者
