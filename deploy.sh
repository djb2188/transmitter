echo "Starting ... "

# DIR is the dir where we put everything and will be the
# working directory of the service process.
# STAGEDIR is the dir where you just svn'd all your files to. 
# (You can delete the staging dir altogether once you're up and running, if you want.)
DIR=/home/ras3005/boost/orchestrator
STAGEDIR=/home/ras3005/boost/orchestrator-staging/

# Check whether we're inside a virtualenv.
# (See https://stackoverflow.com/a/13864829)
if [ -z "${VIRTUAL_ENV+x}" ]; then
  echo "error: need to be inside a virtualenv"
  exit 1
else 
  echo "virtualenv folder is: $VIRTUAL_ENV"
fi

# Install/update supporting libraries from git into virtualenv.
pip install -r $STAGEDIR/requirements.txt --process-dependency-links --upgrade

# Copy core files into installation.
#if [ ! -d "$DIR/config" ]; then
#  mkdir $DIR/config
#fi
cp $STAGEDIR/app/*.py $DIR

# Create a log folder if it doesn't exist.
if [ ! -d "$DIR/log" ]; then
  mkdir $DIR/log
fi

echo "Done!"

