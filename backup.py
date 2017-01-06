'''
Created on Oct 14, 2016

@author: sebastien.brennion
'''

from docker import Client
import json
import sys
import datetime

class containers():
    def __init__(self,**options):
        print (options)
        self.client = Client(**options)
        
        self.containers_by_ids={}
        self.containers_by_name={}
        for c in self.client.containers():
            self.containers_by_ids[c["Id"]]=c
            if "Name" in c :
                self.containers_by_name[c["Name"]]=self.containers_by_ids[c["Id"]]
        
        self.print()
        
    def list(self):
        return self.containers
    
    def get_container_config(self,string):
        if string in self.containers_by_ids:
            return self.containers_by_ids[string]
        elif string in  self.containers_by_name:
            return self.containers_by_name[string]
        else :
            print("Could not find container to backup : %s" % string, file=sys.stderr)

        
    def get_properties(self,properties=[]):
        results=[]
        for c in self.containers:
            row={"Id":c["Id"]}
            for p in properties:
                row[p]=c[p]
            results.append(row)
        return results
                
            
            
    def print(self):
        print(json.dumps(self.containers_by_ids, indent=4, sort_keys=False))
        
    def backup(self,containers_to_backup=[],**options):
        if containers_to_backup==[]: #backup all
            to_backup=self.containers_by_ids.keys()
        else :
            to_backup=containers_to_backup
        
        backup_objects=[]
        for c in to_backup:
            myc=container(self.get_container_config(c), self.client)
            backup_objects.append(myc)
            
        
class container:
    def __init__(self,config,client):
        self.config=config
        self.client=client
        if "Names" in config:
            self.name=config["Names"][0].strip("/")
        else:
            self.name=config["Id"]
            
        if "Mounts" in self.config :
            if len(self.config["Mounts"])==0:
                print("container %s : nothing to do, no volume" % self.name)
                return 0
            else :
                self.backup()
        else :
            print("container %s : nothing to do, no volume" % self.name)
    
    def backup(self):
        #create target container
        backup_repository="leanbi/dataiku_backup"
        datet= datetime.datetime.now().strftime("%Y%m%d-%M%S")
        target_name=self.name + "_" + datet
        self.target_container=target_container(self.client,Image=self.config["Image"],Command=self.config["Command"],Name=target_name)
        print("start backup of %s to %s" % (self.name,target_name) )
        for v in self.config["Mounts"]:
            input_stream, input_stat = self.client.get_archive(self.name,v["Destination"])
            #print("backup volume %s \n stats=%s" % (v["Destination"] , input_stream.read()))
            #open("docker_test.tar","wb").write(input_stream.read())
            print("result volume %s copy= %s" % (v["Destination"],self.client.put_archive(target_name,v["Destination"],input_stream.read())))
        self.target_container.commit(repository=backup_repository)
        self.target_container.remove()
        self.target_container.push_image()
    
class target_container:
    def __init__(self,client,**options):
        self.client=client
        self.name=options["Name"]
        tc=self.client.create_container(image=options["Image"],name=options["Name"],command=options["Command"])
        self.Id=tc["Id"]
        self.start()
    
    def start(self):
        self.client.start(container=self.name)
    def commit(self,repository):
        self.repository=repository
        self.client.commit(container=self.Id,repository="leanbi/dataiku_backup",tag=self.name)
    
    def remove(self):
        print("remove container %s" % self.name)
        self.client.remove_container(container=self.Id,v=True,force=True)
        
    def push_image(self):
        print("pushing image %s" % self.name)
        response = self.client.push(repository= self.repository,tag=self.name)
        print(response)
        self.remove_image()
    
    def remove_image(self):
        print("removing image %s" % self.name)
        response = self.client.remove_image(image="%s:%s" % (self.repository,self.name))

myc= containers(base_url='tcp://localhost:2375')
myc.backup()