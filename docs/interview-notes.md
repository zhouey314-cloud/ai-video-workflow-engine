# Interview notes

1. **Why?** To make ai video workflow engine an inspectable portfolio artifact.
2. **Hardest problem?** Failure and retry states.
3. **Why this architecture?** Keep policy and workflow logic independent from transport and external providers.
4. **Where is AI?** The design marks provider boundaries; any disconnected model remains unverified.
5. **What stays human?** Final review, business truth and any external release decision.
6. **How verified?** Run the tests and sample commands in README; inspect their exact scope.
7. **Failure learned?** The mock output is not a finished video.
8. **Redo?** Add reviewed cases and a narrower production migration path.
9. **Production scale?** Add real auth, durable storage, observability, privacy review and provider-backed evals where relevant.
10. **My contribution?** Independent clean-room code, tests, docs and public release; no company source copied.
