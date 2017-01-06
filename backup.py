import docker
import json
import os
import optparse

class backup():
    def __init__(self,args):
        self.client=docker.from_env()
        self.to_backup=[]

        if args.get("source-container",None)!=None:
            self.from_container_name(args)


    def from_image(self, image):
        allc= self.client.containers.list(all=True)
        print(allc[0].attrs["Config"]["Image"])

    def from_container_name(self,args):
        self.to_backup=[self.client.containers.get(args["source-container"])]
        self.backup(args)

    def backup(self,args):
        for c in self.to_backup:
            print ("starting backup for %s" % c.name)
            backup_container(c,self.client,args)


class backup_container():
    def __init__(self, container,client,args):
        self.target_repository=args["target-repository"]
        self.target_tag=args["target-tag"]
        self.client=client
        self.container=container
        self.target_container=self.create_target_container()
        self.volumes=self.container.attrs["Mounts"]
        self.volumes_tared = []

        self.backup_volumes()
        print("    commit container %s to repository %s:%s" % (self.target_container.name,self.target_repository,self.target_tag))
        self.target_container.commit(self.target_repository,self.target_tag)
        #self.target_container.remove(force=True)

    def create_target_container(self):
        tc= self.client.containers.run("busybox","ping 127.0.0.1",detach=True)
        return tc


    def backup_volumes(self):
        tmp_file = "backup.tar"

        for v in self.volumes:
            destination=v["Destination"]
            target_dir = os.path.abspath(os.path.join(destination, os.pardir))
            cmd_mkdir="mkdir -p %s" % target_dir
            self.target_container.exec_run(cmd_mkdir)
            print ("    Backup volume : %s  unpack to %s | config : %s" %(destination,target_dir,v))


            with open(tmp_file,"wb") as outfile:
                print("    write tempfile %s" % tmp_file)
                archive=self.container.get_archive(v["Destination"])[0].read()
                outfile.write(archive)

            with open(tmp_file,"rb") as infile:
                print("    upload tempfile %s to container" % tmp_file)
                self.target_container.put_archive(target_dir, infile.read())

            print("    remove tempfile %s" % tmp_file)
            os.remove(tmp_file)



if __name__=="__main__" :
    parser=optparse.OptionParser()
    parser.add_option("--source-container")
    parser.add_option("--target-repository")
    parser.add_option("--target-tag")

    options, args = parser.parse_args()
    print ("cmdline options=%s" % options)
    b=backup()
