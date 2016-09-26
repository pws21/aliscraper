for i in `ps -aux|grep HashedControlPassword|grep RunAsDaemon|awk '{print $2}'`
do
  kill -9 $i
done
