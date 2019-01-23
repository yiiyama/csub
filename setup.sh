THISDIR=$(cd $(dirname $BASH_SOURCE); pwd)
echo $PATH | grep -q "$THISDIR/bin:" || export PATH=$THISDIR/bin:$PATH
