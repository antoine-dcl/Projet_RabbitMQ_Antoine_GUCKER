#!/usr/bin/env python
import pika
import time ## à virer

def main() :

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost'))
    channel = connection.channel()        

    Player_name = input("Enter your name : ")

    # Player's queue
    try : 
        channel.queue_delete(queue=Player_name)
    except : 
        pass

    channel.queue_declare(queue=Player_name, durable = False)

    channel.exchange_declare(exchange='host_to_players', exchange_type='direct')

    channel.queue_bind(
        exchange='host_to_players', queue=Player_name, routing_key="player")
    channel.queue_purge(queue=Player_name)

    # Host's queues
    channel.queue_declare(queue='add_players', durable = False)
    channel.queue_declare(queue='host_queue', durable = False)



    channel.basic_publish(exchange='',
                        routing_key='add_players',
                        body=Player_name)
    print ("Please wait for host.")




    
    def callback(ch, method, properties, body):        

        Body = body.decode()
        header = Body[:4] # The first 4 characters are beyond : "info" / "ack " / "vote" / "elim"
        message = Body[4:]

        if header == "info" : 
            # Display message
            print(message)
            return


        elif header == "ack " : 
            # Message to display and to acknowledge after binding its queue
            print(message)


            channel.queue_bind(
                exchange='host_to_players', queue=Player_name, routing_key="werewolf")

            channel.basic_publish(exchange='',
                        routing_key='host_queue',
                        body='')


        elif header == "vote" :
            # Ask the player to vote 
            print(message)
            Vote = input()

            channel.basic_publish(exchange='',
                            routing_key='host_queue',
                            body=Vote)

            print("SENT !")
            return

        elif header == "elim" : 
            # Player is eliminated, or end of the game
            print(message)
            channel.stop_consuming()
            return

        else : 
            print("bad message : " + Body)


    channel.basic_consume(
        queue=Player_name, on_message_callback=callback, auto_ack=True)


    channel.start_consuming()

    channel.queue_delete(queue=Player_name)
    connection.close()

    



if __name__ == "__main__" : 
    main()
