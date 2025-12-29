[![Hugging Face's logo](https://huggingface.co/front/assets/huggingface_logo-noborder.svg) Hugging Face](https://huggingface.co/)
  * [](https://huggingface.co/models)
  * [](https://huggingface.co/datasets)
  * [](https://huggingface.co/spaces)
  * [](https://huggingface.co/docs)
  * [](https://huggingface.co/enterprise)
  * [Pricing](https://huggingface.co/pricing)
  * * * *
  * [Log In](https://huggingface.co/login)
  * [Sign Up](https://huggingface.co/join)


# 
[ ![](https://cdn-avatars.huggingface.co/v1/production/uploads/6707994a087a2d81d8dd76f1/16AlslP0v2xJqzkD0JT2l.png) ](https://huggingface.co/software-mansion)
[software-mansion](https://huggingface.co/software-mansion)
/
[react-native-executorch-qwen-3](https://huggingface.co/software-mansion/react-native-executorch-qwen-3)
like 4
Follow
![](https://cdn-avatars.huggingface.co/v1/production/uploads/6707994a087a2d81d8dd76f1/16AlslP0v2xJqzkD0JT2l.png) Software Mansion 56
[ Text Generation ](https://huggingface.co/models?pipeline_tag=text-generation)[ executorch ](https://huggingface.co/models?other=executorch)[ conversational ](https://huggingface.co/models?other=conversational)
License: apache-2.0
[](https://huggingface.co/software-mansion/react-native-executorch-qwen-3)[Files Files and versions xet ](https://huggingface.co/software-mansion/react-native-executorch-qwen-3/tree/main)[](https://huggingface.co/software-mansion/react-native-executorch-qwen-3/discussions)
  * [Introduction](https://huggingface.co/software-mansion/react-native-executorch-qwen-3#introduction "Introduction")
    * [Compatibility](https://huggingface.co/software-mansion/react-native-executorch-qwen-3#compatibility "Compatibility")
      * [Repository Structure](https://huggingface.co/software-mansion/react-native-executorch-qwen-3#repository-structure "Repository Structure")


#  [ ](https://huggingface.co/software-mansion/react-native-executorch-qwen-3#introduction) Introduction 
This repository hosts the **Qwen 3** models for the [React Native ExecuTorch](https://www.npmjs.com/package/react-native-executorch) library. It includes **unquantized** and **quantized** versions of the Qwen model in `.pte` format, ready for use in the **ExecuTorch** runtime.
If you'd like to run these models in your own ExecuTorch runtime, refer to the [official documentation](https://pytorch.org/executorch/stable/index.html) for setup instructions.
##  [ ](https://huggingface.co/software-mansion/react-native-executorch-qwen-3#compatibility) Compatibility 
If you intend to use this model outside of React Native ExecuTorch, make sure your runtime is compatible with the **ExecuTorch** version used to export the `.pte` files. For more details, see the compatibility note in the [ExecuTorch GitHub repository](https://github.com/pytorch/executorch/blob/11d1742fdeddcf05bc30a6cfac321d2a2e3b6768/runtime/COMPATIBILITY.md?plain=1#L4). If you work with React Native ExecuTorch, the constants from the library will guarantee compatibility with runtime used behind the scenes.
These models were exported using `v0.6.0` version and **no forward compatibility** is guaranteed. Older versions of the runtime may not work with these files.
###  [ ](https://huggingface.co/software-mansion/react-native-executorch-qwen-3#repository-structure) Repository Structure 
The repository is organized into three main directories:
  * `qwen-3-0.6B`
  * `qwen-3-1.7B`
  * `qwen-3-4B`


Each directory contains different versions of the model, including **quantized** , and the **original** models.
  * The `.pte` file should be passed to the `modelSource` parameter.
  * The tokenizer for the models is available within the repo root, under `tokenizer.json` and `tokenizer_config.json`



Downloads last month
    1,432 
Inference Providers [NEW](https://huggingface.co/docs/inference-providers)
[Text Generation](https://huggingface.co/tasks/text-generation "Learn more about text-generation")
This model isn't deployed by any Inference Provider. [🙋 Ask for provider support](https://huggingface.co/spaces/huggingface/InferenceSupport/discussions/new?title=software-mansion/react-native-executorch-qwen-3&description=React%20to%20this%20comment%20with%20an%20emoji%20to%20vote%20for%20%5Bsoftware-mansion%2Freact-native-executorch-qwen-3%5D\(%2Fsoftware-mansion%2Freact-native-executorch-qwen-3\)%20to%20be%20supported%20by%20Inference%20Providers.%0A%0A\(optional\)%20Which%20providers%20are%20you%20interested%20in%3F%20\(Novita%2C%20Hyperbolic%2C%20Together%E2%80%A6\)%0A)
## software-mansion/react-native-executorch-qwen-3
#### [LLM 6 items •  Updated Sep 25 ](https://huggingface.co/collections/software-mansion/llm)
Company
[TOS](https://huggingface.co/terms-of-service) [Privacy](https://huggingface.co/privacy) [About](https://huggingface.co/huggingface) [Careers](https://apply.workable.com/huggingface/) [](https://huggingface.co/)
Website
[Models](https://huggingface.co/models) [Datasets](https://huggingface.co/datasets) [Spaces](https://huggingface.co/spaces) [Pricing](https://huggingface.co/pricing) [Docs](https://huggingface.co/docs)
