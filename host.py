#!/usr/bin/env python
import pika
import random



def main() : 

    global Number_of_players
    global Number_of_werewolves

    # WAITING FOR PLAYERS
    
    # Queue for inscription only
    channel.queue_declare(queue='add_players')

    print( ' [*] Waiting for messages. To exit press CTRL+C')

    def callback(ch, method, properties, body):        

        Body = body.decode()
        print(Body + " has joined.")

        list_of_players.append(Player(Body, None))

        if len(list_of_players) == Number_of_players : 
            channel.stop_consuming()

    channel.basic_consume(on_message_callback=callback, queue='add_players', auto_ack=True)

    channel.start_consuming()
    print("GAME START !")


    channel.queue_declare(queue='host_queue', durable = False)
    channel.queue_purge(queue='host_queue')


    channel.exchange_declare(exchange='host_to_players', exchange_type='direct')



    # ROLE REPARTITION

    Roles = ["Villager" for i in range(Number_of_players)]
    for w in range(Number_of_werewolves) : 
        Roles[w] = "Werewolf"
    random.shuffle(Roles)


    def ack_callback(ch, method, properties, body) : 
        channel.stop_consuming()

    # Give each player his role
    for i in range(Number_of_players) : 
        list_of_players[i].Role = Roles[i]

        message = "Your role is : " + Roles[i]
        if Roles[i] == "Werewolf" : 
            message = "ack " + message
        else : 
            message = "info" + message
            
        channel.basic_publish(
            exchange='', routing_key=list_of_players[i].Name, body=message)

        if Roles[i] == "Werewolf" :
            # Wait for ack from werewolves
            # Because werewolves have to bind their queue with routing_key="werewolf"
            channel.basic_consume(on_message_callback=ack_callback, 
                                queue='host_queue', auto_ack=True)
            channel.start_consuming()

    
    # GAME LOOP
    
    while True : 
        murder_by_werewolves()

        if check_victory(Number_of_werewolves, Number_of_players) : 
            return        

        village_vote()

        if check_victory(Number_of_werewolves, Number_of_players) : 
            return


def check_victory(Number_of_werewolves, Number_of_players): 
    """Check if the game is finished. If so, tell it to players and make them leave the game."""
    winners = None
    if Number_of_werewolves == Number_of_players :        
        winners =  "Werewolves"

    elif Number_of_werewolves == 0 :
        winners = "Villagers"

    if winners is not None :
        message = "elim" + winners + " have won !"
        channel.basic_publish(
            exchange='host_to_players', routing_key="player", body=message)
        return True
    return False
            

    
    
def murder_by_werewolves() :
    """werewolves vote at unanimity to eliminate one other player."""
    
    message = "info" + "Werewolves are : \n"
    killers = []
    victims = []
    for i in range(Number_of_players) : 
        if list_of_players[i].Role == "Werewolf" : 
            message += list_of_players[i].Name + "\n"
            killers.append(list_of_players[i])
        else : 
            victims.append(list_of_players[i])
    
    channel.basic_publish(
        exchange='host_to_players', routing_key="werewolf", body=message)

    
    murder = Vote(killers, victims, routing_key="werewolf")
    Elected = murder.vote()

    # Elimination
    if Elected is not None and murder.result[Elected] == len(killers) : 
        elimination(victims[Elected])


def village_vote() :
    """The village vote to eliminate one of them."""
    
    election = Vote(list_of_players, list_of_players)
    Elected = election.vote()

    message = "info" + "Result of the vote : \n"
    for i in range(Number_of_players) : 
        message += list_of_players[i].Name + " : " + str(election.result[i]) + "\n"

    channel.basic_publish(
            exchange='host_to_players', routing_key="player", body=message)

    if Elected is not None : 
        # Elimination
        elimination(list_of_players[Elected])


def elimination(player) : 
    global Number_of_players
    global Number_of_werewolves

    # Tell the player about the current elimination
    message = "info" + player.Name + " is eliminated. He was " + player.Role + " ."
    channel.basic_publish(
        exchange='host_to_players', routing_key="player", body=message)

    # Make the eliminated player leave the game
    message = "elim" + "You are eliminated."
    channel.basic_publish(
        exchange='', routing_key=player.Name, body=message)

    list_of_players.remove(player)
    Number_of_players -= 1
    if player.Role == "Werewolf" : 
        Number_of_werewolves -= 1


    

    
            
class Vote : 
    def __init__(self, voters, voted, routing_key = "player") :
        self.count = 0
        self.result = [0 for i in range(len(voted))]
        self.voters = voters
        self.voted = voted  
        self.routing_key = routing_key 
        

    def vote(self) : 
        # Ask for vote
        message = "vote" + "Please vote for one player : "
        for i in range(len(self.voted)) : 
            message += "\n" + str(i) + " : " + self.voted[i].Name


        channel.basic_publish(
            exchange='host_to_players', routing_key= self.routing_key, body=message)

        

        def vote_callback(ch, method, properties, body):#(count, body): 
            
            self.count += 1

            Body = body.decode()

            try :
                k = int(Body)
                self.result[k] += 1
            except :
                pass

            if self.count == len(self.voters) : 
                channel.stop_consuming()
                print("Vote finished ")
        
        
        # Collect the ballots
        channel.basic_consume(#on_message_callback=lambda ch, method, properties, body: vote_callback(count, body),
            on_message_callback=vote_callback, 
            queue='host_queue', auto_ack=True)

        channel.start_consuming()

        
        # Return the most chosen player
        try :
            M = max(self.result)
            c = self.result.count(M)

            if c == 1 :
                return self.result.index(M)   

        except : 
            return 


class Player : 
    def __init__(self, Name, Role) :
        self.Name = Name
        self.Role = Role


    

if __name__ == "__main__" : 

    list_of_players = []

    Number_of_players = int(input("Number of players : "))
    Number_of_werewolves = max(Number_of_players // 4, 1)

    
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost'))
    channel = connection.channel()



    main()
    connection.close()
    

    