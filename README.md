The pipeline has three steps:
1. Grid search on personalities to figure out their min and max rates and months to pay off. Will make step 2 more effective.
2. Gradient boosted regression trees to optimize each customers rate with months to pay off loan. 
3. Binary Integer Linear Programming (BILP) to solve the knapstack problem. But since awards cost is unknown we also use Gradient boosted regression trees to estimate the cost on the awards used.
    - Here we also have an option to only go with award "IkeaFoodCoupon" every third month or change every sixth month to "IkeaDeliveryCheck" (due to the late changes of the rules). 


Setup enviroment and install packages

```
conda create --name considition python==3.11.10 -y 

conda activate considition

conda install ipykernel -y

pip install -r requirements.txt

```


docker

```

docker compose down
docker pull sywor/considition2024:latest
docker compose up -d

```


run pipeline (only with Docker)

```

python main.py --part all --change_award

```
