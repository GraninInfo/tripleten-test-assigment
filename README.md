## Quickstart: running the Docker container

### Anthropic API / Bedrock / Vertex

When adding support for the Nebius AI platform, no old functionality was changed or removed, so please see the relevant sections from the [source repository](https://github.com/anthropics/anthropic-quickstarts/tree/a78013a3c8d7c120d2ad6cfb9f6f40edab4c4815/computer-use-demo).

### Nebius AI

> [!TIP]
> You can set up your API key in the [Nebius AI Studio](https://studio.nebius.com/).

```bash
docker build computer_use -t computer-use-nebius-ai
```

```bash
export NEBIUS_API_KEY=%your_api_key%
docker run \
    -e NEBIUS_API_KEY=$NEBIUS_API_KEY \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it computer-use-nebius-ai
```

Once the container is running, open your browser to [http://localhost:8080](http://localhost:8080) to access the combined interface that includes both the agent chat and desktop view.

### Adaptation Process

The main goal was to add support for the Nebius AI to the existing application. The existing application already supports working with Anthropic models, so I chose to add support for querying Nebius AI in the same format as Anthropic, this is implemented in the [computer_use/computer_use_demo/custom_providers/nebius.py](https://github.com/GraninInfo/tripleten-test-assigment/blob/main/computer_use/computer_use_demo/custom_providers/nebius.py) file. With this approach, the number of changes that need to be made to the existing code is minimal, which reduces the number of potential bugs.

While testing the code, I discovered that all four vision models in Nebius AI Studio do not support tool calling. So I added a [pipeline](https://github.com/GraninInfo/tripleten-test-assigment/blob/36bafe52564efe3033c6e1023b716c7cba8ef516/computer_use/computer_use_demo/custom_providers/nebius.py#L193) with two model invocations: one for the vision model that returns a response with a textual description of the tools to use, and one for the model that supports tool calling so that it returns the tool calling information in a structured format.

### Suggestions for evaluation

First of all, to measure such agent performance we need to have a dataset. Since our agent is not very common, we will not be able to find a public dataset. So we need to create it by ourselfs.

To do this, we can ask some LLM model. For example, we can provide the LLM with a list of available tools and a description of our AI agent, and ask it to generate a set of user queries along with the tools that are expected to be called.
We can generate queries that are expected to call only one tool or no tools at all, as well as queries that are expected to call multiple tools during pipeline execution to simulate more complex queries.

Then, having the dataset, we can run our Agent on it and check, which tools Agent called. For each sample from the dataset there can be multiple results:
1. The agent successfully called only those tools that were expected. This does not guarantee that the agent worked completely correctly, since we do not check the parameters of the called tools, but it is a strong positive signal.
2. If the agent did not call all the tools that were expected, this can be considered a significant error.
3. If the agent performed all the expected tool calls, plus a few extra ones, this is a minor error, as it probably achieved the desired result in the end.

Now we can see what proportion of the dataset fell into each of the three options, and use that to evaluate the quality of the model.

Additionally, it is necessary to measure the total cost of the agent’s work. This is also an important metric.

And we can measure another metric, the importance of which depends on the specific task - the average time it takes to respond to each user request.

### Web project testing

#### Project description

The test web page includes a circle that can change color, two buttons "Change to Orange" and "Change to Purple" that should change the color of the circle when clicked, and two buttons "Hover for Red" and "Hover for Pink" that should change the color of the circle when hovered over.

The following bugs were added to the web page:

1. The "Change to Purple" button changes the color of the circle to white instead of purple.
2. The "Hover for Red" button does not work at all.

#### Final prompt crafting

At first, I used a simple prompt, in which I asked to test a web page and write a summary with the results of the testing. And the model wrote the entire list of tests in the first response message along with the list of tools to be called (because of this, all the tools were called in a row) and the final summary, which should have appeared only in the last conversation message.

After seeing this problem, in the next version of the prompt I described what the model should do based on the previous conversation, and it worked: the model started to consistently follow the correct algorithm:
1. Take a screenshot
2. Describe the functionality of the page and list the tests that need to be performed
3. Perform each test separately
4. Write a final summary