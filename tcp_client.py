import socket
target_host = "127.0.0.1"
target_port = 9998
#创建一个socket对象
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# 连接
client_socket.connect((target_host, target_port))
# 发送消息
client_socket.send(b"hello world")
# 接受返回的数据
response = client_socket.recv(4096)

print(response.decode('utf-8'))

client_socket.close()