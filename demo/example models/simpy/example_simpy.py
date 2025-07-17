import simpy
import csv
import argparse

# customer process representing an individual entity that uses the shared resource
def customer(env, name, resource, service_time, log):
    # time of arrival in the simulation → log the arrival event
    arrival_time = env.now  
    log.append([name, 'arrived', arrival_time])

    # request access to the shared resource
    with resource.request() as req:  
        # wait until the resource is available → log when resource is obtained
        yield req  
        log.append([name, 'got resource', env.now]) 

        # hold the resource for the given service time → log the time when service is done
        yield env.timeout(service_time) 
        log.append([name, 'finished', env.now]) 

# sets up and runs the discrete-event simulation
def run_simulation(num_customers, interarrival_time, service_time, resource_capacity, simulation_duration, output_file):
    # create a new simulation environment
    env = simpy.Environment()

    # create a resource with defined capacity
    resource = simpy.Resource(env, capacity=resource_capacity)

    # create a list to collect simulation events
    log = [] 

    # schedule customer arrivals at regular interarrival_time intervals
    for i in range(num_customers):
        # start a customer process and wait before the next customer arrives
        env.process(customer(env, f'Customer{i+1}', resource, service_time, log))
        yield env.timeout(interarrival_time)

    # run the simulation until the specified duration
    env.run(until=simulation_duration)

    # write the simulation log to a CSV file
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Entity', 'Event', 'Time'])
        writer.writerows(log)

# parses command-line arguments and launches the simulation
def main():
    parser = argparse.ArgumentParser(
        description='SimPy DoE Model with configurable parameters',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--customers', type=int, default=5, help='Number of customer processes')
    parser.add_argument('--interarrival', type=float, default=2.0, help='Time between customer arrivals')
    parser.add_argument('--service_time', type=float, default=5.0, help='Time each customer holds the resource')
    parser.add_argument('--capacity', type=int, default=1, help='Capacity of the shared resource')
    parser.add_argument('--duration', type=float, default=30.0, help='Total simulation time')
    parser.add_argument('--output', type=str, default='simpy_output.csv', help='Name of the output CSV file')

    args = parser.parse_args()

    # run_simulation is a generator because it yields on interarrival delay;
    # this loop steps through the generator manually to execute it
    sim = run_simulation(
        num_customers=args.customers,
        interarrival_time=args.interarrival,
        service_time=args.service_time,
        resource_capacity=args.capacity,
        simulation_duration=args.duration,
        output_file=args.output
    )
    try:
        next(sim)
        while True:
            next(sim)
    except StopIteration:
        pass

# entry point for command-line execution
if __name__ == "__main__":
    main()