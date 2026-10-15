# Who else does this (checked on the web, 2026-10-15)

Each row names only what the source says. Where something couldn't be confirmed, the row says so.

| Product | What it does | Where Lucidity differs | Source |
|---|---|---|---|
| Google Colab Data Science Agent | Gemini in a Colab Enterprise notebook: upload a CSV (or a BigQuery table), it splits the data, trains and compares models like a random forest, and tests the best on a held-out set | The same agent that builds the model also runs the test, in the same notebook. In Lucidity the agents can't run the test split; only Lucidity scores it. It also runs on your laptop, not in a Google Cloud project | [Google Cloud docs](https://docs.cloud.google.com/colab/docs/use-data-science-agent) |
| Weco (built on AIDE) | A tree-search agent that edits code, runs your evaluation script and keeps the version with the best metric; AIDE's repo cites OpenAI's MLE-Bench, where its tree search won about 4x more medals than a linear agent | Closest idea. Weco is one search loop on one file; Lucidity races several agents, each on a different model family in its own worktree, and the owner picks which families run. Couldn't confirm whether Weco stops the agent from reading the test score | [Weco docs](https://docs.weco.ai/quickstart/setup-your-own-optimization), [AIDE ML repo](https://github.com/harit7/aideml) |
| AutoGluon | Open-source AutoML: `TabularPredictor.fit` trains and stacks many models on a table, with quality presets | No LLM and no code to review: it's a strong fixed recipe. Lucidity's agents write readable code the owner can merge or reject, and explain the pick. AutoGluon would make a good family for an agent to try | [AutoGluon fit API](https://auto.gluon.ai/dev/api/autogluon.tabular.TabularPredictor.fit.html) |
| DataRobot | Enterprise AutoML and agent platform, priced by quote; a third-party site cites a median contract of about $212,000 a year from Vendr data (not confirmed with DataRobot) | Built for companies with an ML team and a contract. A Lucidity run on a table cost 0.5 to 4.5 cents in model calls on the user's own key (see `tokenomics.md`) | [CasRAI pricing guide](https://www.casrai.org/guides/datarobot-pricing) |

## The gap

The tools that use an LLM to build models (Colab's agent, Weco) score the model inside the same loop that builds it.
AutoML tools don't use an agent at all. Lucidity sits between them: AI agents build the model, and a separate referee
the agents can't reach grades it on a locked test set.
