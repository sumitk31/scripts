echo "Any existing pyenv environment in /nobackup/$USER will be removed. Continue Y/N"
read yes
if [[ "$yes" == "Y" ]];
then
cd /nobackup/$USER
rm -rf pyenv
mkdir pyenv
git clone https://github.com/pyenv/pyenv.git /nobackup/$USER/pyenv
cd pyenv && src/configure && make -C src

echo "export PYENV_ROOT=\"/nobackup/$USER/pyenv\"">>~/.bashrc
echo "export PATH=\"\$PYENV_ROOT/bin:\$PATH\"">>~/.bashrc
#eval "$(pyenv init --path)"
#eval "$(pyenv init -)"

echo "eval \"\$(pyenv init --path)\"">>~/.bashrc
echo "eval \"\$(pyenv init -)\"">>~/.bashrc
export PYENV_ROOT="/nobackup/$USER/pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
pyenv install 3.8.0
#pyenv install 3.4.0
echo "alias pyversions='pyenv versions'">>~/.bashrc
echo "alias pyshell='pyenv shell'">>~/.bashrc
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
pyenv shell 3.8.0
pip install pexpect
cp ~sukala/spitsim.py ~/
echo "alias lspitsim='python ~/scripts/spitsim.py simlog'">>~/.bashrc
else
echo "Exiting..."
fi




