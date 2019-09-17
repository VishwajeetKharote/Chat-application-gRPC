

# Copyright 2015 gRPC authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The Python implementation of the gRPC route guide server."""

from concurrent import futures
from threading import Lock, Thread
import time
import math

import grpc

import config_pb2
import config_pb2_grpc

import yaml
_ONE_DAY_IN_SECONDS = 60 * 60 * 24

def yaml_load(filepath):
        with open(filepath,"r")as file_descriptor:
            data = yaml.load(file_descriptor)
            return data
            
filepath = 'config.yaml'
data = yaml_load(filepath)
port = data.get('port')
lock = Lock()

class GroupMessagingServicer(config_pb2_grpc.GroupMessagingServicer):

    group1=[]
    group2=[]
    current_User=[]
    msgGrpDict={}
    onlineGrpDict={}
    grpMemberMapping = {}
    ratelimitingdictionary={}

    def __init__(self):
        self.max_num_messages_per_user = data.get('max_num_messages_per_user')
        self.max_call_per_30_seconds_per_user=data.get('max_call_per_30_seconds_per_user')
        self.valid_user = data.get('users')
        self.groups = data.get('groups')
        i=0
        templist = []
        for g in self.groups:
            templist.append(self.groups.get(g))
        
        for i in range(1,len(templist)+1):
            globals()['group'+str(i)] = templist[i-1]
            self.grpMemberMapping.update({str(i):templist[i-1]})

        for i in range(len(self.valid_user)):
            self.msgGrpDict[self.valid_user[i]] = []

        for i in range(len(self.valid_user)):
            self.ratelimitingdictionary[self.valid_user[i]] = []
        
        for i in range(1,len(templist)+1):
            self.onlineGrpDict.update({str(i):list()})

    def authenticateGrpUser(self,request,context):
        username = request.name
        if username in self.msgGrpDict.keys():
            self.current_User.append(username)
            for key, value in self.grpMemberMapping.items():
                for v in value:
                    if username == v:
                        groupId=key
            onlineList = self.onlineGrpDict.get(groupId)
            onlineList.append(username)
            return config_pb2.serverGrpResponse(isAuthenticated=True,grpnum=groupId)
        else:
            return config_pb2.serverGrpResponse(isAuthenticated=False,grpnum='0')


    def getGroupMembers(self,request,context):
        groupId = request.name
        listofMembers = list()
        if groupId in self.grpMemberMapping.keys():
            listofMembers = self.grpMemberMapping.get(str(groupId))
            return config_pb2.getList(names=listofMembers)
        else:
            return config_pb2.getList(names=[])


    def sendMsgToGrp(self,request,context):
        groupId = request.groupid
        groupMemList = self.grpMemberMapping.get(groupId)
        # lock.acquire()
        # templist = self.ratelimitingdictionary.get(request.sender) 
        # lock.release()
        # if len(templist)<self.max_call_per_30_seconds_per_user:
        for users in groupMemList:
            if users != request.sender:
                storeMessages = self.msgGrpDict.get(users)
                if(len(storeMessages)<self.max_num_messages_per_user):
                    storeMessages.append(request)
                    self.msgGrpDict[users] = storeMessages
                    # lock.acquire()
                    # templist.append("1")
                    # self.ratelimitingdictionary[request.sender] = templist
                    # lock.release()
                else:
                    storeMessages.pop(0)
                    storeMessages.append(request)
                    self.msgGrpDict[users] = storeMessages
        print(self.msgGrpDict)
        return config_pb2.sendMsgAck(success=True)
        # else:
        #     return config_pb2.sendMsgAck(success=False)

    def recvMsgFromGrp(self,request,context):
        receiverName = request.name
        messageList = self.msgGrpDict.get(receiverName)
        i = 0
        for key, value in self.grpMemberMapping.items():
                for v in value:
                    if receiverName == v:
                        groupId=key
        onlineList = self.onlineGrpDict.get(str(groupId))
        if receiverName in onlineList:
            for messages in messageList:
                messageList.pop(i)
                yield messages
                i+=1

    def checkGrpMsg(self,request,context):
        username = request.name
        messageList = self.msgGrpDict.get(username)
        if messageList is None:
            return config_pb2.serverResponse(isAuthenticated=False)
        elif(len(messageList)>0):
             return config_pb2.serverResponse(isAuthenticated=True)        
        else:
             return config_pb2.serverResponse(isAuthenticated=False)

    def offlineGrpMsgs(self,request,context):

        receiverName = request.name
        offlineMessageGrpList = self.msgGrpDict.get(receiverName)
        senderList = []
        msgList=[]
        timeList=[]
        for offlineMessage in offlineMessageGrpList:
            senderList.append(offlineMessage.sender)
            msgList.append(offlineMessage.msgSend)
            timeList.append(offlineMessage.time)
        return config_pb2.getOfflineMsgs(sender=senderList,msgSend=msgList,time=timeList)

    def acknowledgeServerGrp(self,request,context):
        name = request.name
        prevList = self.msgGrpDict.get(name)
        prevList = []
        self.msgGrpDict[name] = prevList
        return config_pb2.Empty()

    def checkOfflineGrpMsg(self,request,context):
        username = request.name
        offlineMessageList = self.msgGrpDict.get(username)
        if(len(offlineMessageList)>0):
            return config_pb2.serverResponse(isAuthenticated=True)
        else:
            return config_pb2.serverResponse(isAuthenticated=False)
    
    def getActiveUsers(self,request,context):
        groupId = request.name
        activelist = self.onlineGrpDict.get(groupId)
        return config_pb2.getList(names=activelist)

    def checkMsgLimit(self):
        time.sleep(30)
        lock.acquire()
        self.limitCheck=[]
        lock.release()

    def logout(self,request,context):
        username = request.name
        for key, value in self.grpMemberMapping.items():
                for v in value:
                    if username == v:
                        groupId=key
        onlineList = self.onlineGrpDict.get(groupId)  
        if username in onlineList:
            onlineList.remove(username) 
        return config_pb2.Empty()       
    


    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    config_pb2_grpc.add_GroupMessagingServicer_to_server(
        GroupMessagingServicer(), server)
        
    
    server.add_insecure_port('[::]:'+str(port))
    server.start()
    
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()


############################################ One to one Chat Application code #################################################



# class MessagingServicer(config_pb2_grpc.MessagingServicer):
#     """Provides methods that implement functionality of route guide server."""
#     valid_User = []
#     current_User=[]
#     #msg=[]
#     dictionary = {}
#     offlinedictionary = {}
#     notificationdictionary = {}
#     notificationSentdictionary = {}
#     offlineReceiver = []
#     requestRejectionList = []
    
#     def __init__(self):
#         self.valid_User = ['Vishu', 'Vishwajeet', 'Nikhil', 'Foo', 'Shri', 'Rutvik']
#         #self.isAuthenticated = False
#         self.dictionary = {
#             'Vishu': [],
#             'Foo' : [],
#             'Shri': [],
#             'Rutvik':[]
#         }   
#         self.offlinedictionary = {
#             'Vishu': [],
#             'Foo' : [],
#             'Shri': [],
#             'Rutvik':[]
#         }

#         self.notificationdictionary = {
#             'Vishu': [],
#             'Foo' : [],
#             'Shri': [],
#             'Rutvik':[]
#         }
#         self.notificationSentdictionary={
#             'Vishu': [],
#             'Foo' : [],
#             'Shri': [],
#             'Rutvik':[]        
#         }

#         self.requestRejection = []
    

    

#     def acknowledgeServer(self,request,context):
#         username = request.name
#         offlineMsglist=[]
#         offlineMsglist = self.offlinedictionary.get(username)
#         offlineMsglist = []
#         self.offlinedictionary[username] = offlineMsglist
#         return config_pb2.Empty()

#     def authenticateUser(self,request,context):
#         if request.name in self.valid_User:
#             self.current_User.append(request.name)
#             print("Current Users are",self.current_User)
#             return config_pb2.serverResponse(isAuthenticated=True)
#         else:
#             return config_pb2.serverResponse(isAuthenticated=False)

#     def authenticateReceiver(self,request,context):
#         if request.name in self.valid_User:
#             return config_pb2.serverResponse(isAuthenticated=True)
#         else:
#             return config_pb2.serverResponse(isAuthenticated=False)
    
#     def getCurrentUsers(self,request,context):
#         if request.name in self.valid_User:
#             currentUserList = self.current_User
#             return config_pb2.activeusers(activeUsers=currentUserList)
#         else:
#             currentUserList = []
#             return config_pb2.activeusers(activeUsers=currentUserList)

#     def sendMsg(self, request, context):
#         username=request.sender
#         receiver=request.receiver
#         msgtoSend = request.msgSend

#         if(username in self.valid_User and receiver in self.valid_User):
#             messageList = self.dictionary.get(receiver)
#             if receiver in self.current_User: 
#                 messageList.append(request)
#                 self.dictionary[receiver] = messageList
#             else:
#                 self.offlineReceiver.append(receiver)
#                 offlineMessageList = self.offlinedictionary.get(receiver)
#                 if(len(offlineMessageList)<10):
#                     print("Offline mode append")
#                     offlineMessageList.append(request)
#                 else:
#                     offlineMessageList.pop(0)
#                     print("Pop out this element:")
#                     offlineMessageList.append(request)
#                 self.offlinedictionary[receiver] = offlineMessageList
#             #self.dictionary[receiver] = messageList
#             #self.msg.append(request)
#             #self.msg.append(msgtoSend)
#             print("Messages List",self.offlinedictionary)
#             print("Messages List",self.dictionary)
#             return config_pb2.Empty()
    
#     def checkMsg(self, request, context):
#         username = request.name
#         messageList = self.dictionary.get(username)
#         if messageList is None:
#             return config_pb2.serverResponse(isAuthenticated=False)
#         elif(len(messageList)>0):
#             #for message in messageList:
#              return config_pb2.serverResponse(isAuthenticated=True)        
#         else:
#              return config_pb2.serverResponse(isAuthenticated=False)
    
#     def checkOfflineMsg(self,request,context):
#         username = request.name
#         offlineMessageList = self.offlinedictionary.get(username)
#         if(len(offlineMessageList)>0):
#             #for message in offlineMessageList:
#             return config_pb2.serverResponse(isAuthenticated=True)
#         else:
#             return config_pb2.serverResponse(isAuthenticated=False)
             
#     def recvMsg(self,request,context):
#         receiverName = request.name
#         messageList = self.dictionary.get(receiverName)
#         i = 0
#         #print("This is the length",len(messageList))
#         for messages in messageList:
#             if messages.receiver == receiverName:
#                 print(messages)
#                 messageList.pop(i)
#                 yield messages
#             i+=1
#         # for messages in self.msg:
#         #     x = config_pb2.serverMsg(fromUser = "Vishu", toUser = "Foo", msgRecv = "This")
#         #     yield x

#     def offlineMessages(self,request,context):

#         receiverName = request.name
#         offlineMessageList = self.offlinedictionary.get(receiverName)
#         senderList = []
#         msgList=[]
#         timeList=[]
#         for offlineMessage in offlineMessageList:
#             senderList.append(offlineMessage.sender)
#             msgList.append(offlineMessage.msgSend)
#             timeList.append(offlineMessage.time)
#         return config_pb2.offlineMessageList(offlinefromUser=senderList,offlineMsg=msgList,offlinetimeSent=timeList)
#         # i = 0
#         # #print("This is the length",len(messageList))
#         # for messages in offlineMessageList:
#         #     if messages.receiver == receiverName:
#         #         print(messages)
#         #         offlineMessageList.pop(i)
#         #         yield messages
#         #     i+=1
#     def appendNotification(self,request,context):

#         sendername = request.sender
#         receivername = request.receiver

#         sList = self.notificationSentdictionary.get(sendername)
#         sList.append(receivername)
#         self.notificationSentdictionary[sendername] = sList 

#         rList = self.notificationdictionary.get(receivername)
#         print("==This is rlist==", rList)
#         print("This is the rlist object",sendername)
#         rList.append(sendername)
#         print("==This is rlist==",rList)
#         #rList.append(sendername)
#         self.notificationdictionary[receivername] = rList
#         return config_pb2.Empty()

#         # sender = request.sender
#         # receiver = request.receiver
#         # senderList = self.notificationSentdictionary.get(sender)
#         # senderList.append(receiver)
#         # self.notificationSentdictionary[sender] = senderList
#         # receiverList1 = list()
#         # receiverList =self.notificationdictionary.get(receiver)
#         # receiverList1 = receiverList
#         # receiverList1.append(sender)
#         # self.notificationdictionary[receiver] = receiverList1
#         # print("appending")
#         # print(receiverList)
#         # receiverList = self.notificationdictionary.get(receiver)
#         # receiverList1 = list(receiverList)
#         # receiverList1.append(sender)
#         # senderList = self.notificationSentdictionary.get(sender)
#         # senderList1 = list(senderList)
#         # senderList1.append(receiver)
#         #receiverList.append(sender)

#     def getNotification(self,request,context):
#         username = request.name
#         listToSend=list()
#         notificationSend = self.notificationdictionary.get(username)
#         for users in notificationSend:
#             if users in self.current_User:
#                 listToSend.append(users)
#                 print(listToSend)
#             else:
#                 pass
#         return config_pb2.notificationResponse(notificationFrom=listToSend)

#     def newChat(self,request,context):
#         sender = request.name
#         notifysentList = self.notificationSentdictionary.get(sender)
#         notifysentList = []
#         self.notificationSentdictionary[sender] = notifysentList
#         self.requestRejectionList.append(sender)
#         return config_pb2.Empty()
        
#     def clearRejectionList(self,request,context):
#         print("server clearRejectionList function")
#         removeRejectedUser = request.name
#         print("This is the rejection list===========")
#         print(self.requestRejectionList)
#         print("This is the rejection list===========")
#         if removeRejectedUser in self.requestRejectionList:
#             self.requestRejectionList.remove(removeRejectedUser)
#             return config_pb2.Empty()
    
#     def checkName(self,request,context):
#         rejectedsender = request.name
#         print("Server Check name function")
#         if rejectedsender in self.requestRejectionList:
#             return config_pb2.rejectedList(names=self.requestRejectionList)
#         else:
#             return config_pb2.rejectedList(names=[])
    
#     def alertNotification(self,request,context):
#         username = request.name
#         notificationSend = self.notificationdictionary.get(username)
#         if len(notificationSend)>0:
#             return config_pb2.serverResponse(isAuthenticated=True)
#         else:
#             return config_pb2.serverResponse(isAuthenticated=False)

#     def clearNotificationList(self,request,context):
#         username = request.name
#         notificationSend = self.notificationdictionary.get(username)
#         self.notificationdictionary[username]=[]
#         return config_pb2.Empty()





