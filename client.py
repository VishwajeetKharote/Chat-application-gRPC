from __future__ import print_function
from multiprocessing.pool import ThreadPool
pool = ThreadPool(processes=1)

import sys
import grpc
import time
import config_pb2 
import config_pb2_grpc 
import threading 
import yaml
#from Crypto.Cipher import AES
import AES

def yaml_load(filepath):
        with open(filepath,"r")as file_descriptor:
            data = yaml.load(file_descriptor)
            return data
def addpadding(text):
        return text+((16-len(text)%16)*'`')

filepath = 'config.yaml'
data = yaml_load(filepath)
port = data.get('port')
symmetric_key = data.get('key')
padded_symmetric_key= addpadding(symmetric_key)
cipher = AES.new(padded_symmetric_key)
address = 'localhost'


class GroupChat:

    groupid=''
    limitCheck=[]
    def __init__(self,username):
        self.username = username
        channel = grpc.insecure_channel(address + ':' + str(port))
        self.conn2 = config_pb2_grpc.GroupMessagingStub(channel)

    def authenticateGrpUser(self,username):
        responseUname = self.conn2.authenticateGrpUser(config_pb2.clientRequest(name=username))
        self.groupid=responseUname.grpnum
        return responseUname

    def getGroupMembers(self,username):
        listofMembers = self.conn2.getGroupMembers(config_pb2.clientRequest(name= self.groupid))
        return listofMembers.names

    def sendMessage(self,groupId,username,msg,timeToSend):
        encryptedMessage = self.encrypt(msg)
        success = self.conn2.sendMsgToGrp(config_pb2.groupMsg(groupid=self.groupid,sender=username,msgSend=encryptedMessage,time=timeToSend))
        return success
            
    def convertEpochToNormal(self,epochTime):
        return time.strftime('%H:%M:%S %p', time.localtime(epochTime))


    def receiveOfflineMessages(self):
        askForMessages = input("[Spartan] Do you wish to see messsage?  Type 'Yes' to See and 'No' To ignore")                  
        if(askForMessages == 'Yes' or askForMessages == 'Y' or askForMessages == 'yes' or askForMessages == 'y'):
            offlineMessageList = self.conn2.offlineGrpMsgs(config_pb2.clientRequest(name=self.username))
            offlineUserList = offlineMessageList.sender
            offlineMsgList = offlineMessageList.msgSend
            offlinetimeSent = offlineMessageList.time
            length= len(offlinetimeSent)
            for i in range(0,length):
                decyptedMessage = self.decrypt(offlineMsgList[i])
                print('['+offlineUserList[i]+'] '+decyptedMessage)
            self.conn2.acknowledgeServerGrp(config_pb2.clientRequest(name=self.username))
        else:
            self.conn2.acknowledgeServerGrp(config_pb2.clientRequest(name=self.username))
            

    def pingForOfflineMessages(self):
        ifMsg = self.conn2.checkOfflineGrpMsg(config_pb2.clientRequest(name=self.username))
        if(ifMsg.isAuthenticated):
            self.receiveOfflineMessages()

    def pingForGrpMessages(self):
        while(True):
            ifMsg = self.conn2.checkGrpMsg(config_pb2.clientRequest(name=self.username))
            if(ifMsg.isAuthenticated):
                self.receiveMessages()
            else:
                pass

    def receiveMessages(self):
        while(True):  
            receivedMessagesList = self.conn2.recvMsgFromGrp(config_pb2.clientRequest(name=self.username))
            for receivedMessage in receivedMessagesList:
                decryptedMsg = self.decrypt(receivedMessage.msgSend)
                if len(decryptedMsg)>0:
                    print('\n'+'['+receivedMessage.sender+ '] '+decryptedMsg)

    def getActiveUser(self):
        activeUserList = []
        activeUserList=self.conn2.getActiveUsers(config_pb2.clientRequest(name=self.groupid))
        print("[Spartan] Current Active users in group are:",activeUserList.names)

    
    
    def encrypt(self,plaintext):
        global cipher
        return cipher.encrypt(addpadding(plaintext))

    def decrypt(self,ciphertext):
        global cipher
        dec = cipher.decrypt(ciphertext).decode('utf-8')
        l = dec.count('`')
        return dec[:len(dec)-l] 

    def logoutGrp(self):
        self.conn2.logout(config_pb2.clientRequest(name=self.username))


def run():
    try:
        username = sys.argv[1]
        print("[Spartan] Connected to Spartan Server at port "+str(port))
        
        grpObj = GroupChat(username)
        validUsername = grpObj.authenticateGrpUser(username)
        if(validUsername.isAuthenticated):
            membersofgroup = grpObj.getGroupMembers(username)
            print("[Spartan] User list: ",membersofgroup)
            print("[Spartan] You are now ready to chat in group.")
            grpObj.pingForOfflineMessages()
            grpObj.getActiveUser()
            threading.Thread(target=grpObj.pingForGrpMessages, daemon=True).start()
            
            #threading.Thread(target=grpObj.checkMsgLimit, daemon=True).start()
            while(True):
                msgToSend = input('['+username+'] > ')
                if(msgToSend == 'exit' or msgToSend == 'logout'):
                    grpObj.logoutGrp()
                    print("You decided to logout\nVisit again...!!!")
                    break
                timeToSend = time.time()
                success = grpObj.sendMessage(grpObj.groupid,username,msgToSend,timeToSend)
    except KeyboardInterrupt:
            grpObj.logoutGrp()
            print("You decided to logout\nVisit again...!!!")          


if __name__ == '__main__':
    run()


