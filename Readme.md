# Vision language interaction Agent

## Description:
An Rl agent which takes in RGB input with language input to produce actions [0-17]:
* 0 - no-op
* 1 - step forward
* 2 - step backward
* 3 - step left
* 4 - step right
* 5 - jump
* 6-11 - inventory select
* 12 - move the camera left
* 13 - move the camera right
* 14 - move the camera up
* 15 - move the camera down
* 16 - break block
* 17 - place block

## Files:
### vli_network.py : 
contains the network code used to train and test on IGLU dataset. Used RLib to train and test.
Use [this](https://gitlab.aicrowd.com/aicrowd/challenges/iglu-challenge-2022/iglu-2022-rl-task-starter-kit/) link to know more about dataset and the tasks.

## Results with local_evalution.py;
For each task, I calculate F1 score between built and target structures as asked. 
below shown is the average of task for each skill.

| Agent        | Flying           | Flat | all|
| ------------- |:-------------:| -----:| -----:
| HCAM using agent(ours) | 0.154|0.172 | 0.163
